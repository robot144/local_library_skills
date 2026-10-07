#!/usr/bin/env python3
"""Estimate how long converting a PDF with marker-pdf will take, without running
the conversion. Uses per-page rates measured in real conversions (see SKILL.md
"Rough timing"); GPU/CPU detection is best-effort (checks for nvidia-smi /
vulkaninfo, doesn't probe what llama-server would actually pick at runtime).
Treat the result as a rough guide for deciding whether to confirm with the
user before a long conversion, not a precise forecast - formula/table-dense
content can take meaningfully longer than these flat per-page rates assume,
especially on CPU (every display equation goes through the VLM regardless of
--force_ocr, so CPU + default mode on an equation-dense document is the least
predictable case).

Usage: python3 estimate.py input.pdf [--force_ocr]

Prints a human-readable line, then a machine-parseable `key=value` summary
line (pages=, device=, mode=, seconds=) for scripted/agent use.

Windows/cross-platform counterpart of estimate.sh - see SKILL.md's
"Platform check" section for when to use which.
"""
import sys
from pathlib import Path

from _pdf2md_common import gpu_available, page_count

SEC_PER_PAGE = {
    ("GPU", True): 10,
    ("GPU", False): 3,
    ("CPU", True): 150,
    ("CPU", False): 15,
}


def human_time(s):
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60} min"
    return f"{s // 3600}h {(s % 3600) // 60}m"


def main():
    args = sys.argv[1:]
    if len(args) < 1:
        print(f"usage: {sys.argv[0]} input.pdf [--force_ocr]", file=sys.stderr)
        return 1

    pdf = Path(args[0])
    if not pdf.is_file():
        print(f"error: file not found: {pdf}", file=sys.stderr)
        return 1

    force_ocr = "--force_ocr" in args

    pages = page_count(pdf)
    if pages is None:
        print(
            "Could not determine page count (pdfinfo unavailable, or install "
            "one if missing); no time estimate available.",
            file=sys.stderr,
        )
        print("pages=unknown device=unknown mode=unknown seconds=unknown")
        return 0

    device = "GPU" if gpu_available() else "CPU"
    sec_per_page = SEC_PER_PAGE[(device, force_ocr)]
    mode = "--force_ocr" if force_ocr else "default"
    total_seconds = pages * sec_per_page

    device_note = "GPU detected" if device == "GPU" else "No GPU detected"

    extra_caveat = ""
    if device == "CPU" and not force_ocr:
        extra_caveat = (
            " Note: this is the least predictable case - every display equation "
            "goes through the VLM regardless of --force_ocr, so a formula-dense "
            "document could take several times longer than this estimate (seen "
            "up to ~18x in testing)."
        )

    print(
        f"{device_note}. Converting this {pages}-page document ({mode} mode) is "
        f"estimated to take around {human_time(total_seconds)} "
        f"(~{sec_per_page}s/page, rough estimate - formula/table-dense content "
        f"can be slower).{extra_caveat}"
    )
    print()
    print(f"pages={pages} device={device} mode={mode} seconds={total_seconds}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
