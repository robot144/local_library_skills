"""Shared helpers for the pdf-to-markdown Python scripts (install.py,
uninstall.py, estimate.py, pdf2md.py). Not a public entrypoint itself.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PAGES_RE = re.compile(r"^Pages:\s*(\d+)", re.MULTILINE)


def log(msg):
    print(f"\n==> {msg}")


def default_env_dir():
    env = os.environ.get("PDF2MD_ENV_DIR")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "pdf2md-env"


def hf_hub_cache_dir():
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        return Path(cache)
    home = os.environ.get("HF_HOME")
    base = Path(home) if home else Path.home() / ".cache" / "huggingface"
    return base / "hub"


def page_count(pdf):
    if shutil.which("pdfinfo") is None:
        return None
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf)], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    m = PAGES_RE.search(result.stdout)
    return int(m.group(1)) if m else None


def gpu_available():
    if os.environ.get("LLAMA_CPP_NGL") == "0":
        return False
    if shutil.which("nvidia-smi") is not None:
        try:
            if subprocess.run(
                ["nvidia-smi", "-L"], capture_output=True, check=False
            ).returncode == 0:
                return True
        except OSError:
            pass
    if shutil.which("vulkaninfo") is not None:
        try:
            if subprocess.run(
                ["vulkaninfo", "--summary"], capture_output=True, check=False
            ).returncode == 0:
                return True
        except OSError:
            pass
    return False


def require_pixi():
    if shutil.which("pixi") is None:
        print("error: pixi not found on PATH", file=sys.stderr)
        sys.exit(1)


def run_pixi(env_dir, *args, **kwargs):
    return subprocess.run(
        ["pixi", "run", "--manifest-path", str(env_dir), *args], **kwargs
    )
