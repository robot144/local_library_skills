#!/usr/bin/env python3
"""Scaffold a Quarto browsing site into a local-library root: pixi.toml
(quarto dependency), _quarto.yml (website project, sidebar auto-nav from
the folder tree), and index.qmd (landing page). Never overwrites a file
that already exists.

For the pixi.toml specifically: if the library root doesn't already have
one, this searches upward through ancestor directories for an existing
pixi.toml (e.g. a project root one level up) and merges the `quarto`
dependency into *that* one instead of creating a new, separate manifest at
the library root. Only falls back to creating a fresh one if no ancestor
manifest exists. This avoids leaving a second, incomplete pixi.toml nested
inside a project that already has one - `pixi run` picks whichever
manifest is nearest to the current directory with no fallback to a parent,
so a nested manifest that's missing a dependency the outer one has (e.g.
`python`) silently shadows the working one for anything run from inside
the library, which can be a nasty surprise, especially if a `python3`
shim on PATH re-invokes `pixi run python` - see the `python3`-shim note in
SKILL.md's Quarto section.

After scaffolding, run `python3 sync-quarto-pages.py <library-root>` (and
re-run after converting more PDFs to markdown) to generate the per-document
.qmd wrapper pages, then `cd <library-root> && pixi install && pixi run
quarto preview` - this works whether the manifest lives in the library root
or an ancestor directory, since `pixi` itself searches upward too.

Usage: python3 init-quarto.py [path/to/library-root]
Defaults to ./local_library if no path is given.
"""
import re
import sys
from pathlib import Path

QUARTO_DEP_MARKER = "# added by local-library init-quarto.py"
QUARTO_KEY_RE = re.compile(r"^\s*quarto\s*=", re.MULTILINE)

DEFAULT_ROOT = "local_library"

PIXI_TOML_TEMPLATE = """\
[workspace]
name = "local-library-quarto"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["linux-64"]

[dependencies]
quarto = ">=1.9,<2"
"""

QUARTO_YML_TEMPLATE = """\
project:
  type: website
  output-dir: _site
  render:
    - index.qmd
    - CLAUDE.md
    - INDEX.md
    - "**/INDEX.md"
    - "**/*.qmd"

website:
  title: "Local Library"
  sidebar:
    style: "docked"
    title: " "
    contents: auto

format:
  html:
    theme: cosmo
    toc: true
    mainfont: sans-serif
    css: styles.css
"""

STYLES_CSS_TEMPLATE = """\
.sidebar-item-text {
  font-weight: 600;
}

/* "Library Index" is always the 2nd top-level sidebar item (right after
   Home) - make it stand out from the topic entries below it. */
.sidebar-menu-container > ul.list-unstyled > li.sidebar-item:nth-child(2) .sidebar-item-text {
  font-size: 1.1em;
  color: var(--bs-link-color);
}

.sidebar-menu-container > ul.list-unstyled > li.sidebar-item:nth-child(2) {
  border-bottom: 1px solid var(--bs-border-color, #dee2e6);
  padding-bottom: 0.4em;
  margin-bottom: 0.4em;
}
"""

INDEX_QMD_TEMPLATE = """\
---
title: "Home"
---

Browse the library structure in the sidebar, or jump straight to:

- [Library Index](INDEX.md) — full contents (topics + top-level documents)
- [CLAUDE.md](CLAUDE.md) — what this library is and how it's organized

Each document entry links to its PDF and, where available, its converted markdown version.
"""

GITIGNORE_TEMPLATE = """\
_site/
.pixi/
.quarto/
"""


def write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        print(f"==> {path.name} already exists, leaving it untouched: {path}")
    else:
        path.write_text(content, encoding="utf-8")
        print(f"==> Created {path}")


def merge_quarto_into(manifest: Path) -> str:
    """Add the quarto dependency to an existing pixi.toml. Returns 'added'
    or 'already-present' (idempotent - safe to call on every run)."""
    text = manifest.read_text(encoding="utf-8")
    if QUARTO_KEY_RE.search(text):
        return "already-present"
    line = f'quarto = ">=1.9,<2"  {QUARTO_DEP_MARKER}'
    if "[dependencies]" in text:
        text = text.replace("[dependencies]", f"[dependencies]\n{line}", 1)
    else:
        text = text.rstrip("\n") + f"\n\n[dependencies]\n{line}\n"
    manifest.write_text(text, encoding="utf-8")
    return "added"


def setup_pixi_manifest(root: Path) -> Path:
    """Return the pixi.toml that will provide the quarto dependency: the
    library's own if one already exists there; otherwise the nearest
    ancestor manifest (quarto merged in); otherwise a newly-created one at
    the library root."""
    own = root / "pixi.toml"
    if own.is_file():
        print(f"==> pixi.toml already exists, leaving it untouched: {own}")
        return own

    for d in root.parents:
        candidate = d / "pixi.toml"
        if candidate.is_file():
            status = merge_quarto_into(candidate)
            verb = "Added quarto to" if status == "added" else "quarto already present in"
            print(f"==> {verb} existing manifest: {candidate}")
            return candidate

    own.write_text(PIXI_TOML_TEMPLATE, encoding="utf-8")
    print(f"==> Created {own}")
    return own


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1
    root = root.resolve()

    manifest = setup_pixi_manifest(root)
    write_if_missing(root / "_quarto.yml", QUARTO_YML_TEMPLATE)
    write_if_missing(root / "index.qmd", INDEX_QMD_TEMPLATE)
    write_if_missing(root / "styles.css", STYLES_CSS_TEMPLATE)
    write_if_missing(root / ".gitignore", GITIGNORE_TEMPLATE)

    print(
        f"\nDone. Quarto environment: {manifest}\n"
        f"Next steps:\n"
        f"  python3 sync-quarto-pages.py {root}\n"
        f"  cd {root} && pixi install && pixi run quarto preview"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
