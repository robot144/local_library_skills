#!/usr/bin/env bash
# Install marker-pdf (PDF -> markdown) into a dedicated pixi environment, shared
# across every project that uses this skill (so no target repo gets a pixi.toml
# or model cache dropped into it just for PDF conversion).
#
# Usage:  ./install.sh [env_dir]      (default: $PDF2MD_ENV_DIR or ~/.local/share/pdf2md-env)
#
# Safe to re-run: existing manifests are extended, not replaced, and pixi add
# is a no-op if the dependency is already present.
#
# Also restores the executable bit on every script in this directory: some
# install methods (confirmed: `gh skill install`) don't preserve it, which
# would otherwise break direct invocation (`scripts/pdf2md.sh ...`) with a
# plain "Permission denied" even though the file content is untouched. Run
# this script itself via `bash scripts/install.sh` the first time if it
# isn't executable yet - after that, every script here (including this one)
# is fixed for subsequent direct invocation.
set -euo pipefail

chmod +x "$(dirname "${BASH_SOURCE[0]}")"/*.sh 2>/dev/null || true

ENV_DIR="${1:-${PDF2MD_ENV_DIR:-$HOME/.local/share/pdf2md-env}}"
mkdir -p "$ENV_DIR"
ENV_DIR="$(cd "$ENV_DIR" && pwd)"

cd "$ENV_DIR"
log() { printf '\n==> %s\n' "$*"; }

command -v pixi >/dev/null || { echo "error: pixi not found on PATH" >&2; exit 1; }

log "Installing marker-pdf into: $ENV_DIR"

# --- 1. pixi manifest --------------------------------------------------------
if [ -f pixi.toml ]; then
    MANIFEST=pixi.toml
else
    MANIFEST=pixi.toml
    log "Creating pixi.toml"
    pixi init --format pixi .
fi

# --- 2. dependencies ----------------------------------------------------------
# Python 3.12: marker-pdf pins pillow 10.4, which has no wheels for newer Pythons.
# llama.cpp: conda-forge package, includes the llama-server binary; pulls in
# whatever runtime libs it needs (libgomp, mkl, a Vulkan GPU backend, ...) transitively.
log "Adding conda dependencies (python 3.12, llama.cpp)"
pixi add "python>=3.12,<3.13" "llama.cpp"

log "Adding marker-pdf from PyPI"
pixi add --pypi "marker-pdf>=2.0.0,<3"

# --- 3. activation environment -----------------------------------------------
# marker's surya dependency auto-detects an NVIDIA GPU and defaults to its vllm
# backend, which needs Docker. Avoid that failure mode by launching llama-server
# locally instead. Note this does NOT force CPU-only inference: if a Vulkan- or
# CUDA-capable GPU is present, llama-server and PyTorch's layout model will both
# auto-offload to it anyway (confirmed via nvidia-smi) - that's normal and fast,
# not a bug. To force genuine CPU-only (e.g. for a controlled benchmark), export
# LLAMA_CPP_NGL=0 and TORCH_DEVICE=cpu when running pdf2md.sh.
if grep -q 'SURYA_INFERENCE_BACKEND' "$MANIFEST"; then
    log "Activation env already configured"
else
    log "Adding SURYA_INFERENCE_BACKEND to [activation.env]"
    env_lines='SURYA_INFERENCE_BACKEND = "llamacpp"'
    if grep -qF '[activation.env]' "$MANIFEST"; then
        tmp="$(mktemp)"
        awk -v hdr='[activation.env]' -v lines="$env_lines" \
            '{ print } $0 == hdr { print lines }' "$MANIFEST" > "$tmp"
        cat "$tmp" > "$MANIFEST" && rm -f "$tmp"
    else
        printf '\n%s\n%s\n' '[activation.env]' "$env_lines" >> "$MANIFEST"
    fi
fi

# --- 4. install and verify ---------------------------------------------------
log "Installing environment"
pixi install

log "Verifying"
pixi run llama-server --version 2>&1 | head -1
pixi run marker_single --help >/dev/null
echo "marker_single OK"

cat <<EOF

Done. Environment ready at: $ENV_DIR

The first conversion downloads ~1.8GB of models from Hugging Face into
~/.cache/huggingface (setting HF_TOKEN raises rate limits).

Note: llama-server's own CPU-thread auto-detect can badly under-use hybrid
(P+E core) CPUs, resolving to as few as 4 threads on a 24-core machine. If
conversions seem CPU-underutilized, set LLAMA_CPP_EXTRA_ARGS="-t N -tb N"
in $ENV_DIR/pixi.toml's [activation.env], where N is your P-core count
(mixing in E-cores can be *slower*, not faster - llama.cpp's decode loop
barrier-syncs every thread each token, so the slowest thread sets the pace).
EOF
