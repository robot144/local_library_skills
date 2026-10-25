"""Shared pytest fixtures/helpers for testing the skills' scripts.

These are unit tests for the scripts' own deterministic logic (file
scaffolding, parsing, cleanup scoping) - they never invoke pixi, quarto,
or snakemake themselves. That's a separate, heavier integration concern;
see plan.md's "Testing" section for why the two are kept apart.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script(relative_path: str):
    """Import a skill script by file path and return its module object.

    Needed because script filenames like `init-workflow.py` contain
    hyphens, which aren't valid in a Python module name - a plain `import`
    statement can't reach them. `relative_path` is relative to the repo
    root, e.g. "skills/workflow/scripts/init-workflow.py".
    """
    path = REPO_ROOT / relative_path
    module_name = path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def load_script():
    """Fixture form of _load_script, for use as `def test_x(load_script):
    module = load_script("skills/.../foo.py")`."""
    return _load_script
