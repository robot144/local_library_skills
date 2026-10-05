#!/usr/bin/env bash
# Remove the dedicated marker-pdf pixi environment created by install.sh.
#
# Usage:  ./uninstall.sh [--models] [env_dir]
#         (default env_dir: $PDF2MD_ENV_DIR or ~/.local/share/pdf2md-env)
#
# Deletes the whole environment directory (pixi.toml, pixi.lock, .pixi/) -
# safe to do wholesale because install.sh always creates a fresh, dedicated
# environment there and never reuses or edits an existing project's manifest,
# unlike installing marker-pdf directly into a project (see the non-skill
# install/uninstall scripts this was adapted from, which do surgical manifest
# edits for exactly that reason).
#
# --models additionally deletes the downloaded models (~1.8 GB): these live in
# shared/global caches (~/.cache/datalab, ~/.cache/huggingface), not inside
# env_dir, so they're off by default even when removing the environment itself.
set -euo pipefail

REMOVE_MODELS=0
if [ "${1:-}" = "--models" ]; then
    REMOVE_MODELS=1
    shift
fi
ENV_DIR="${1:-${PDF2MD_ENV_DIR:-$HOME/.local/share/pdf2md-env}}"

log() { printf '\n==> %s\n' "$*"; }

if [ -d "$ENV_DIR" ]; then
    # Sanity check before rm -rf: refuse to touch anything that doesn't look
    # like an environment install.sh actually created, or an obviously unsafe
    # path - guards against a misconfigured PDF2MD_ENV_DIR.
    resolved="$(cd "$ENV_DIR" && pwd)"
    if [ "$resolved" = "/" ] || [ "$resolved" = "$HOME" ]; then
        echo "error: refusing to remove $resolved (looks like a root or home directory, not an env_dir)" >&2
        exit 1
    fi
    if [ ! -f "$ENV_DIR/pixi.toml" ]; then
        echo "error: $resolved doesn't contain a pixi.toml; doesn't look like an install.sh environment, refusing to remove" >&2
        echo "If you're sure, remove it manually: rm -rf \"$resolved\"" >&2
        exit 1
    fi
    log "Removing environment: $resolved"
    rm -rf "$resolved"
else
    log "No environment found at $ENV_DIR; nothing to remove"
fi

if [ "$REMOVE_MODELS" = 1 ]; then
    hf_hub="${HF_HUB_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}/hub}"
    log "Removing models from ~/.cache/datalab and $hf_hub/models--datalab-to--*"
    rm -rf "$HOME/.cache/datalab"
    rm -rf "$hf_hub"/models--datalab-to--*
fi

echo
echo "Done."
[ "$REMOVE_MODELS" = 1 ] || echo "Downloaded models were kept (~1.8 GB in ~/.cache/datalab and ~/.cache/huggingface); pass --models to remove them too."
