#!/usr/bin/env python3
"""Convert a PDF to markdown with marker-pdf, auto-installing into a shared pixi
environment on first use (see install.py).

Usage: python3 pdf2md.py input.pdf [marker_single options...]

Output goes next to the PDF: docs/foo.pdf -> docs/foo/foo.md (+ images, meta.json),
unless --output_dir is given.
Run `python3 pdf2md.py --help` for marker_single's options.

Large PDFs (more pages than PDF2MD_CHUNK_THRESHOLD, default 100) are converted
in page-range chunks of PDF2MD_CHUNK_SIZE pages (default 50) and merged, instead
of one marker_single call for the whole document. This avoids memory exhaustion
seen converting a 651-page manual with --force_ocr in a single process (marker's
per-page state accumulates for the life of the process). Chunking is skipped if
the caller already passed --page_range (they're already scoping the request) or
if `pdfinfo` isn't available to determine the page count.

Environment overrides:
  PDF2MD_ENV_DIR           shared pixi env location (default ~/.local/share/pdf2md-env)
  PDF2MD_CHUNK_THRESHOLD   page count above which chunking kicks in (default 100)
  PDF2MD_CHUNK_SIZE        pages per chunk (default 50)
  PDF2MD_KEEP_CHUNKS       set to keep the per-chunk work dir after a successful
                           merge (default: deleted on success, kept on failure)

Windows/cross-platform counterpart of pdf2md.sh - see SKILL.md's
"Platform check" section for when to use which.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from _pdf2md_common import default_env_dir, hf_hub_cache_dir, log, page_count

IMAGE_PATTERNS = ("_page_*.jpeg", "_page_*.jpg", "_page_*.png")


def main():
    script_dir = Path(__file__).resolve().parent
    env_dir = default_env_dir()
    chunk_threshold = int(os.environ.get("PDF2MD_CHUNK_THRESHOLD", "100"))
    chunk_size = int(os.environ.get("PDF2MD_CHUNK_SIZE", "50"))

    args = sys.argv[1:]
    if len(args) < 1:
        print(f"usage: {sys.argv[0]} input.pdf [marker_single options...]", file=sys.stderr)
        return 1

    if not (env_dir / "pixi.toml").is_file():
        print(f"==> No marker-pdf environment at {env_dir} yet; installing...", file=sys.stderr)
        subprocess.run(
            [sys.executable, str(script_dir / "install.py"), str(env_dir)], check=True
        )

    if args[0] in ("-h", "--help"):
        result = subprocess.run(
            ["pixi", "run", "--manifest-path", str(env_dir), "marker_single", "--help"]
        )
        return result.returncode

    pdf = Path(args[0])
    args = args[1:]
    if not pdf.is_file():
        print(f"error: file not found: {pdf}", file=sys.stderr)
        return 1
    pdf = pdf.resolve()
    name = pdf.stem

    hf_hub = hf_hub_cache_dir()
    if not (hf_hub / "models--datalab-to--surya-ocr-2-gguf").is_dir() or not (
        hf_hub / "models--datalab-to--surya_layout2"
    ).is_dir():
        print(
            f"==> Models not found in {hf_hub}; this run will download ~1.8GB from "
            "Hugging Face (one-time, shared across all environments - subsequent "
            "runs reuse this cache).",
            file=sys.stderr,
        )

    output_dir = None
    passthrough = []
    skip_next = False
    for a in args:
        if skip_next:
            output_dir = a
            skip_next = False
            continue
        if a == "--output_dir":
            skip_next = True
            continue
        passthrough.append(a)
    if not output_dir:
        output_dir = str(pdf.parent)

    has_page_range = "--page_range" in passthrough

    pages = page_count(pdf)

    if pages is None or pages <= chunk_threshold or has_page_range:
        result = subprocess.run(
            ["pixi", "run", "--manifest-path", str(env_dir), "marker_single", str(pdf),
             "--output_dir", output_dir, *passthrough]
        )
        return result.returncode

    print(
        f"==> {pages} pages > {chunk_threshold} threshold; converting in "
        f"{chunk_size}-page chunks",
        file=sys.stderr,
    )

    work_dir = Path(output_dir) / ".pdf2md_chunks" / name
    work_dir.mkdir(parents=True, exist_ok=True)

    last_page = pages - 1
    start = 0
    chunk_dirs = []
    failed = False
    while start <= last_page:
        end = min(start + chunk_size - 1, last_page)
        chunk_idx = start // chunk_size + 1
        label = f"chunk_{chunk_idx:03d}_p{start:06d}-{end:06d}"
        chunk_dir = work_dir / label
        chunk_md = chunk_dir / name / f"{name}.md"
        chunk_dirs.append(chunk_dir / name)

        if chunk_md.is_file():
            print(f"==> {label} already done, skipping", file=sys.stderr)
        else:
            print(
                f"==> {label} (pages {start}-{end}): {time.strftime('%H:%M:%S')}",
                file=sys.stderr,
            )
            t0 = time.time()
            log_path = chunk_dir.parent / f"{chunk_dir.name}.log"
            with open(log_path, "w") as logf:
                result = subprocess.run(
                    ["pixi", "run", "--manifest-path", str(env_dir), "marker_single", str(pdf),
                     "--output_dir", str(chunk_dir), "--page_range", f"{start}-{end}",
                     *passthrough],
                    stdout=logf, stderr=subprocess.STDOUT,
                )
            if result.returncode == 0:
                print(f"==> {label} done in {int(time.time() - t0)}s", file=sys.stderr)
            else:
                print(
                    f"==> {label} FAILED (see {log_path}); other chunks will still be attempted",
                    file=sys.stderr,
                )
                failed = True
        start = end + 1

    if failed:
        print(
            "error: one or more chunks failed; not merging. Re-run to resume "
            "(completed chunks are skipped).",
            file=sys.stderr,
        )
        return 1

    merge_dir = Path(output_dir) / name
    merge_dir.mkdir(parents=True, exist_ok=True)

    merge_md = merge_dir / f"{name}.md"
    with open(merge_md, "w", encoding="utf-8") as out:
        for d in chunk_dirs:
            out.write((d / f"{name}.md").read_text(encoding="utf-8"))
            out.write("\n\n")
            for pattern in IMAGE_PATTERNS:
                for img in sorted(d.glob(pattern)):
                    shutil.copy(img, merge_dir)

    meta_files = [d / f"{name}_meta.json" for d in chunk_dirs if (d / f"{name}_meta.json").is_file()]
    if meta_files:
        toc, stats, debug_path = [], [], None
        for f in meta_files:
            d = json.loads(f.read_text(encoding="utf-8"))
            toc.extend(d.get("table_of_contents") or [])
            stats.extend(d.get("page_stats") or [])
            if debug_path is None:
                debug_path = d.get("debug_data_path")
        (merge_dir / f"{name}_meta.json").write_text(
            json.dumps(
                {"table_of_contents": toc, "page_stats": stats, "debug_data_path": debug_path},
                indent=2,
            ),
            encoding="utf-8",
        )

    if os.environ.get("PDF2MD_KEEP_CHUNKS"):
        print(f"==> Keeping chunk work dir: {work_dir} (PDF2MD_KEEP_CHUNKS set)", file=sys.stderr)
    else:
        shutil.rmtree(work_dir)
        try:
            work_dir.parent.rmdir()
        except OSError:
            pass

    print(f"==> Merged: {merge_dir}/{name}.md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
