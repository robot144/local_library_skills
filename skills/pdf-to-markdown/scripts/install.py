#!/usr/bin/env python3
"""Install marker-pdf (PDF -> markdown) into a dedicated pixi environment, shared
across every project that uses this skill (so no target repo gets a pixi.toml
or model cache dropped into it just for PDF conversion).

Usage: python3 install.py [env_dir]   (default: $PDF2MD_ENV_DIR or ~/.local/share/pdf2md-env)

Safe to re-run: existing manifests are extended, not replaced, and pixi add
is a no-op if the dependency is already present.

Windows/cross-platform counterpart of install.sh - see SKILL.md's
"Platform check" section for when to use which.
"""
import subprocess
import sys
from pathlib import Path

from _pdf2md_common import default_env_dir, log, require_pixi


def main():
    require_pixi()

    env_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else default_env_dir()
    env_dir.mkdir(parents=True, exist_ok=True)
    env_dir = env_dir.resolve()

    log(f"Installing marker-pdf into: {env_dir}")

    manifest = env_dir / "pixi.toml"
    if not manifest.is_file():
        log("Creating pixi.toml")
        subprocess.run(["pixi", "init", "--format", "pixi", str(env_dir)], check=True)

    log("Adding conda dependencies (python 3.12, llama.cpp)")
    subprocess.run(
        ["pixi", "add", "--manifest-path", str(env_dir), "python>=3.12,<3.13", "llama.cpp"],
        check=True,
    )

    log("Adding marker-pdf from PyPI")
    subprocess.run(
        ["pixi", "add", "--manifest-path", str(env_dir), "--pypi", "marker-pdf>=2.0.0,<3"],
        check=True,
    )

    text = manifest.read_text(encoding="utf-8")
    if "SURYA_INFERENCE_BACKEND" in text:
        log("Activation env already configured")
    else:
        log("Adding SURYA_INFERENCE_BACKEND to [activation.env]")
        env_line = 'SURYA_INFERENCE_BACKEND = "llamacpp"'
        if "[activation.env]" in text:
            text = text.replace("[activation.env]", f"[activation.env]\n{env_line}", 1)
        else:
            text += f"\n[activation.env]\n{env_line}\n"
        manifest.write_text(text, encoding="utf-8")

    log("Installing environment")
    subprocess.run(["pixi", "install", "--manifest-path", str(env_dir)], check=True)

    log("Verifying")
    result = subprocess.run(
        ["pixi", "run", "--manifest-path", str(env_dir), "llama-server", "--version"],
        capture_output=True, text=True, check=True,
    )
    lines = (result.stdout or result.stderr).splitlines()
    if lines:
        print(lines[0])
    subprocess.run(
        ["pixi", "run", "--manifest-path", str(env_dir), "marker_single", "--help"],
        stdout=subprocess.DEVNULL, check=True,
    )
    print("marker_single OK")

    print(f"""
Done. Environment ready at: {env_dir}

The first conversion downloads ~1.8GB of models from Hugging Face into
~/.cache/huggingface (setting HF_TOKEN raises rate limits).

Note: llama-server's own CPU-thread auto-detect can badly under-use hybrid
(P+E core) CPUs, resolving to as few as 4 threads on a 24-core machine. If
conversions seem CPU-underutilized, set LLAMA_CPP_EXTRA_ARGS="-t N -tb N"
in {env_dir}/pixi.toml's [activation.env], where N is your P-core count
(mixing in E-cores can be *slower*, not faster - llama.cpp's decode loop
barrier-syncs every thread each token, so the slowest thread sets the pace).""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
