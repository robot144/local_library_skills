#!/usr/bin/env python3
"""Scaffold a Quarto browsing site into a local-library root: pixi.toml
(quarto dependency), _quarto.yml (website project, sidebar auto-nav from
the folder tree), and index.qmd (landing page). Never overwrites a file
that already exists.

After scaffolding, run `python3 sync-quarto-pages.py <library-root>` (and
re-run after converting more PDFs to markdown) to generate the per-document
.qmd wrapper pages, then `cd <library-root> && pixi install && pixi run
quarto preview`.

Usage: python3 init-quarto.py [path/to/library-root]
Defaults to ./local_library if no path is given.
"""
import sys
from pathlib import Path

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
    - "*/INDEX.md"
    - "**/*.qmd"

website:
  title: "Local Library"
  sidebar:
    style: "docked"
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
"""

INDEX_QMD_TEMPLATE = """\
---
title: "Local Library"
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


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1
    root = root.resolve()

    write_if_missing(root / "pixi.toml", PIXI_TOML_TEMPLATE)
    write_if_missing(root / "_quarto.yml", QUARTO_YML_TEMPLATE)
    write_if_missing(root / "index.qmd", INDEX_QMD_TEMPLATE)
    write_if_missing(root / "styles.css", STYLES_CSS_TEMPLATE)
    write_if_missing(root / ".gitignore", GITIGNORE_TEMPLATE)

    print(
        f"\nDone. Next steps:\n"
        f"  python3 sync-quarto-pages.py {root}\n"
        f"  cd {root} && pixi install && pixi run quarto preview"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
