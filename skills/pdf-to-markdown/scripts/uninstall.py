#!/usr/bin/env python3
"""Remove the dedicated marker-pdf pixi environment created by install.py.

Usage: python3 uninstall.py [--models] [env_dir]
       (default env_dir: $PDF2MD_ENV_DIR or ~/.local/share/pdf2md-env)

Deletes the whole environment directory (pixi.toml, pixi.lock, .pixi/) -
safe to do wholesale because install.py always creates a fresh, dedicated
environment there and never reuses or edits an existing project's manifest.

--models additionally deletes the downloaded models (~1.8 GB): these live in
shared/global caches (~/.cache/datalab, ~/.cache/huggingface), not inside
env_dir, so they're off by default even when removing the environment itself.

Windows/cross-platform counterpart of uninstall.sh - see SKILL.md's
"Platform check" section for when to use which.
"""
import shutil
import sys
from pathlib import Path

from _pdf2md_common import default_env_dir, hf_hub_cache_dir, log


def main():
    args = sys.argv[1:]
    remove_models = False
    if args and args[0] == "--models":
        remove_models = True
        args = args[1:]
    env_dir = Path(args[0]) if args else default_env_dir()

    if env_dir.is_dir():
        resolved = env_dir.resolve()
        if resolved == Path(resolved.anchor) or resolved == Path.home().resolve():
            print(
                f"error: refusing to remove {resolved} (looks like a root or home "
                "directory, not an env_dir)",
                file=sys.stderr,
            )
            return 1
        if not (env_dir / "pixi.toml").is_file():
            print(
                f"error: {resolved} doesn't contain a pixi.toml; doesn't look like "
                "an install.py environment, refusing to remove",
                file=sys.stderr,
            )
            print(f'If you\'re sure, remove it manually: rm -rf "{resolved}"', file=sys.stderr)
            return 1
        log(f"Removing environment: {resolved}")
        shutil.rmtree(resolved)
    else:
        log(f"No environment found at {env_dir}; nothing to remove")

    if remove_models:
        hf_hub = hf_hub_cache_dir()
        log(f"Removing models from ~/.cache/datalab and {hf_hub}/models--datalab-to--*")
        shutil.rmtree(Path.home() / ".cache" / "datalab", ignore_errors=True)
        for p in hf_hub.glob("models--datalab-to--*"):
            shutil.rmtree(p, ignore_errors=True)

    print()
    print("Done.")
    if not remove_models:
        print(
            "Downloaded models were kept (~1.8 GB in ~/.cache/datalab and "
            "~/.cache/huggingface); pass --models to remove them too."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
