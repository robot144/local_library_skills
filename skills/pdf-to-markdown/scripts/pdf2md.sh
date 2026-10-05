#!/usr/bin/env bash
# Convert a PDF to markdown with marker-pdf, auto-installing into a shared pixi
# environment on first use (see install.sh).
#
# Usage:  ./pdf2md.sh input.pdf [marker_single options...]
#
# Output goes next to the PDF: docs/foo.pdf -> docs/foo/foo.md (+ images, meta.json),
# unless --output_dir is given.
# Run `./pdf2md.sh --help` for marker_single's options.
#
# Large PDFs (more pages than PDF2MD_CHUNK_THRESHOLD, default 100) are converted
# in page-range chunks of PDF2MD_CHUNK_SIZE pages (default 50) and merged, instead
# of one marker_single call for the whole document. This avoids memory exhaustion
# seen converting a 651-page manual with --force_ocr in a single process (marker's
# per-page state accumulates for the life of the process). Chunking is skipped if
# the caller already passed --page_range (they're already scoping the request) or
# if `pdfinfo` isn't available to determine the page count.
#
# Environment overrides:
#   PDF2MD_ENV_DIR           shared pixi env location (default ~/.local/share/pdf2md-env)
#   PDF2MD_CHUNK_THRESHOLD   page count above which chunking kicks in (default 100)
#   PDF2MD_CHUNK_SIZE        pages per chunk (default 50)
#   PDF2MD_KEEP_CHUNKS       set to keep the per-chunk work dir after a successful
#                            merge (default: deleted on success, kept on failure)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="${PDF2MD_ENV_DIR:-$HOME/.local/share/pdf2md-env}"
CHUNK_THRESHOLD="${PDF2MD_CHUNK_THRESHOLD:-100}"
CHUNK_SIZE="${PDF2MD_CHUNK_SIZE:-50}"

if [ $# -lt 1 ]; then
    echo "usage: $0 input.pdf [marker_single options...]" >&2
    exit 1
fi

# Auto-install on first use.
if [ ! -f "$ENV_DIR/pixi.toml" ]; then
    echo "==> No marker-pdf environment at $ENV_DIR yet; installing..." >&2
    bash "$SCRIPT_DIR/install.sh" "$ENV_DIR"
fi

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    exec pixi run --manifest-path "$ENV_DIR" marker_single --help
fi

PDF="$1"
shift
[ -f "$PDF" ] || { echo "error: file not found: $PDF" >&2; exit 1; }
PDF="$(cd "$(dirname "$PDF")" && pwd)/$(basename "$PDF")"
NAME="$(basename "$PDF" .pdf)"

# Models download on first *conversion* (not at install), into a cache shared
# across every environment on the machine - see SKILL.md "Quick start". Warn
# up front since it's a ~1.8GB download that can otherwise look like a hang.
hf_hub="${HF_HUB_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}/hub}"
if [ ! -d "$hf_hub/models--datalab-to--surya-ocr-2-gguf" ] || [ ! -d "$hf_hub/models--datalab-to--surya_layout2" ]; then
    echo "==> Models not found in $hf_hub; this run will download ~1.8GB from Hugging Face (one-time, shared across all environments - subsequent runs reuse this cache)." >&2
fi

# Pull --output_dir (if given) out of the passthrough args and resolve the default
# (next to the PDF) otherwise. Stripping it lets both the single-shot path and the
# chunked path add their own --output_dir without colliding with the caller's.
OUTPUT_DIR=""
passthrough=()
skip_next=0
for a in "$@"; do
    if [ "$skip_next" = 1 ]; then
        OUTPUT_DIR="$a"
        skip_next=0
        continue
    fi
    if [ "$a" = "--output_dir" ]; then
        skip_next=1
        continue
    fi
    passthrough+=("$a")
done
set -- "${passthrough[@]}"
[ -n "$OUTPUT_DIR" ] || OUTPUT_DIR="$(dirname "$PDF")"

run_marker() {
    pixi run --manifest-path "$ENV_DIR" marker_single "$PDF" "$@"
}

has_page_range() {
    for a in "$@"; do
        [ "$a" = "--page_range" ] && return 0
    done
    return 1
}

page_count() {
    command -v pdfinfo >/dev/null 2>&1 || return 1
    pdfinfo "$1" 2>/dev/null | awk -F': *' '/^Pages:/{print $2}'
}

PAGES="$(page_count "$PDF" || true)"

if [ -z "$PAGES" ] || [ "$PAGES" -le "$CHUNK_THRESHOLD" ] || has_page_range "$@"; then
    exec pixi run --manifest-path "$ENV_DIR" marker_single "$PDF" --output_dir "$OUTPUT_DIR" "$@"
fi

# --- Large PDF: convert in page-range chunks and merge -----------------------
echo "==> $PAGES pages > $CHUNK_THRESHOLD threshold; converting in $CHUNK_SIZE-page chunks" >&2

WORK_DIR="$OUTPUT_DIR/.pdf2md_chunks/$NAME"
mkdir -p "$WORK_DIR"

last_page=$((PAGES - 1))
start=0
chunk_dirs=()
failed=0
while [ "$start" -le "$last_page" ]; do
    end=$((start + CHUNK_SIZE - 1))
    [ "$end" -gt "$last_page" ] && end=$last_page
    label="$(printf "chunk_%03d_p%06d-%06d" $((start / CHUNK_SIZE + 1)) "$start" "$end")"
    chunk_dir="$WORK_DIR/$label"
    chunk_md="$chunk_dir/$NAME/$NAME.md"
    chunk_dirs+=("$chunk_dir/$NAME")

    if [ -f "$chunk_md" ]; then
        echo "==> $label already done, skipping" >&2
    else
        echo "==> $label (pages $start-$end): $(date +%H:%M:%S)" >&2
        t0=$(date +%s)
        if run_marker --output_dir "$chunk_dir" --page_range "${start}-${end}" "$@" \
            > "$chunk_dir.log" 2>&1; then
            echo "==> $label done in $(( $(date +%s) - t0 ))s" >&2
        else
            echo "==> $label FAILED (see $chunk_dir.log); other chunks will still be attempted" >&2
            failed=1
        fi
    fi
    start=$((end + 1))
done

if [ "$failed" -ne 0 ]; then
    echo "error: one or more chunks failed; not merging. Re-run to resume (completed chunks are skipped)." >&2
    exit 1
fi

# --- Merge chunk outputs into the standard <output_dir>/<name>/ layout -------
MERGE_DIR="$OUTPUT_DIR/$NAME"
mkdir -p "$MERGE_DIR"

: > "$MERGE_DIR/$NAME.md"
for d in "${chunk_dirs[@]}"; do
    cat "$d/$NAME.md" >> "$MERGE_DIR/$NAME.md"
    printf '\n\n' >> "$MERGE_DIR/$NAME.md"
    shopt -s nullglob
    for img in "$d"/_page_*.jpeg "$d"/_page_*.jpg "$d"/_page_*.png; do
        cp "$img" "$MERGE_DIR/"
    done
    shopt -u nullglob
done

meta_files=()
for d in "${chunk_dirs[@]}"; do
    [ -f "$d/${NAME}_meta.json" ] && meta_files+=("$d/${NAME}_meta.json")
done
if [ ${#meta_files[@]} -gt 0 ]; then
    pixi run --manifest-path "$ENV_DIR" python -c "
import json, sys
out, inputs = sys.argv[1], sys.argv[2:]
toc, stats, debug_path = [], [], None
for f in inputs:
    d = json.load(open(f))
    toc.extend(d.get('table_of_contents') or [])
    stats.extend(d.get('page_stats') or [])
    if debug_path is None:
        debug_path = d.get('debug_data_path')
json.dump({'table_of_contents': toc, 'page_stats': stats, 'debug_data_path': debug_path},
          open(out, 'w'), indent=2)
" "$MERGE_DIR/${NAME}_meta.json" "${meta_files[@]}"
fi

if [ -n "${PDF2MD_KEEP_CHUNKS:-}" ]; then
    echo "==> Keeping chunk work dir: $WORK_DIR (PDF2MD_KEEP_CHUNKS set)" >&2
else
    rm -rf "$WORK_DIR"
    rmdir "$OUTPUT_DIR/.pdf2md_chunks" 2>/dev/null || true
fi

echo "==> Merged: $MERGE_DIR/$NAME.md" >&2
