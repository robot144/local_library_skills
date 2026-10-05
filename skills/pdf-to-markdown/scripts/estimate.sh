#!/usr/bin/env bash
# Estimate how long converting a PDF with marker-pdf will take, without running
# the conversion. Uses per-page rates measured in real conversions (see SKILL.md
# "Rough timing"); GPU/CPU detection is best-effort (checks for nvidia-smi /
# vulkaninfo, doesn't probe what llama-server would actually pick at runtime).
# Treat the result as a rough guide for deciding whether to confirm with the
# user before a long conversion, not a precise forecast - formula/table-dense
# content can take meaningfully longer than these flat per-page rates assume,
# especially on CPU (every display equation goes through the VLM regardless of
# --force_ocr, so CPU + default mode on an equation-dense document is the least
# predictable case).
#
# Usage: ./estimate.sh input.pdf [--force_ocr]
#
# Prints a human-readable line, then a machine-parseable `key=value` summary
# line (pages=, device=, mode=, seconds=) for scripted/agent use.
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 input.pdf [--force_ocr]" >&2
    exit 1
fi

PDF="$1"
[ -f "$PDF" ] || { echo "error: file not found: $PDF" >&2; exit 1; }

FORCE_OCR=0
for a in "$@"; do
    [ "$a" = "--force_ocr" ] && FORCE_OCR=1
done

page_count() {
    command -v pdfinfo >/dev/null 2>&1 || return 1
    pdfinfo "$1" 2>/dev/null | awk -F': *' '/^Pages:/{print $2}'
}

gpu_available() {
    [ "${LLAMA_CPP_NGL:-}" = "0" ] && return 1  # explicitly forced CPU-only
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
        return 0
    fi
    if command -v vulkaninfo >/dev/null 2>&1 && vulkaninfo --summary >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

PAGES="$(page_count "$PDF" || true)"
if [ -z "$PAGES" ]; then
    echo "Could not determine page count (pdfinfo unavailable, or install one if missing); no time estimate available." >&2
    echo "pages=unknown device=unknown mode=unknown seconds=unknown"
    exit 0
fi

if gpu_available; then
    DEVICE="GPU"
    SEC_PER_PAGE=$([ "$FORCE_OCR" = 1 ] && echo 10 || echo 3)
else
    DEVICE="CPU"
    SEC_PER_PAGE=$([ "$FORCE_OCR" = 1 ] && echo 150 || echo 15)
fi
MODE=$([ "$FORCE_OCR" = 1 ] && echo "--force_ocr" || echo "default")
TOTAL_SECONDS=$((PAGES * SEC_PER_PAGE))

human_time() {
    local s=$1
    if [ "$s" -lt 60 ]; then
        echo "${s}s"
    elif [ "$s" -lt 3600 ]; then
        echo "$((s / 60)) min"
    else
        echo "$((s / 3600))h $(((s % 3600) / 60))m"
    fi
}

if [ "$DEVICE" = "GPU" ]; then
    device_note="GPU detected"
else
    device_note="No GPU detected"
fi

extra_caveat=""
if [ "$DEVICE" = "CPU" ] && [ "$FORCE_OCR" = 0 ]; then
    extra_caveat=" Note: this is the least predictable case - every display equation goes through the VLM regardless of --force_ocr, so a formula-dense document could take several times longer than this estimate (seen up to ~18x in testing)."
fi

cat <<EOF
$device_note. Converting this $PAGES-page document ($MODE mode) is estimated to take around $(human_time "$TOTAL_SECONDS") (~${SEC_PER_PAGE}s/page, rough estimate - formula/table-dense content can be slower).$extra_caveat

pages=$PAGES device=$DEVICE mode=$MODE seconds=$TOTAL_SECONDS
EOF
