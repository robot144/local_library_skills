#!/usr/bin/env python3
"""Scaffold a new multi-page Quarto documentation *project* from this
skill's bundled templates/<kind>/ directory (currently just templates/docs/:
_quarto.yml + index.qmd + installation.qmd + design.md + reference.md +
figures/), with its own self-contained pixi.toml.

This is the "project" counterpart to init-quarto.py's single-document
scaffolding - a docs site has no one file that is "the document" the way
report.qmd/log.qmd/slides.qmd are, so there's no single .qmd to copy and
no per-document frontmatter marker to add; the whole directory is the
unit, and the marker (reporting-skill-doc/reporting-skill-kind) lives as
top-level keys in its _quarto.yml instead - confirmed by testing that
Quarto accepts unrecognized top-level keys there with no warning, same as
how it already carries unrelated custom metadata.

Always a self-contained, nested pixi.toml - never merged into an ancestor
manifest, unlike init-quarto.py's single documents. A docs site is a
substantial, long-lived thing meant to stand on its own (same stance
`workflow` takes), not a quick one-off report sharing an environment with
whatever else is in the same parent project.

Never overwrites an existing project - if the target directory already
has a _quarto.yml, it's left untouched.

Usage: python3 init-docs.py [path/to/project-dir] [--template docs]
Defaults to "./docs" if no path is given. --template exists for symmetry
with init-quarto.py and to leave room for a future second project kind
(e.g. book, architecturally identical to docs - just _quarto.yml's
`book:` key instead of `website:`) - docs is the only one built so far.
"""
import shutil
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
DEFAULT_TEMPLATE = "docs"
DEFAULT_TARGET = "docs"

PIXI_TOML_TEMPLATE = """\
[workspace]
name = "reporting-quarto-docs"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["linux-64"]

[dependencies]
python = ">=3.10,<3.14"
quarto = ">=1.9,<2"
jupyter = ">=1.0,<2"
"""

GITIGNORE_TEMPLATE = """\
_site/
.quarto/
.pixi/
"""


def write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        print(f"==> {path.name} already exists, leaving it untouched: {path}")
    else:
        path.write_text(content, encoding="utf-8")
        print(f"==> Created {path}")


def main() -> int:
    args = sys.argv[1:]
    template = DEFAULT_TEMPLATE
    if "--template" in args:
        i = args.index("--template")
        template = args[i + 1]
        del args[i:i + 2]

    template_dir = TEMPLATES_DIR / template
    if not template_dir.is_dir() or not (template_dir / "_quarto.yml").is_file():
        available = sorted(
            p.name for p in TEMPLATES_DIR.iterdir() if (p / "_quarto.yml").is_file()
        )
        print(
            f"error: no such project template '{template}' (available: {', '.join(available)})",
            file=sys.stderr,
        )
        return 1

    target = Path(args[0] if args else DEFAULT_TARGET)
    if (target / "_quarto.yml").is_file():
        print(f"==> _quarto.yml already exists, leaving the project untouched: {target}")
    else:
        shutil.copytree(template_dir, target, dirs_exist_ok=True)
        print(f"==> Created {target}/ (from templates/{template}/)")

    write_if_missing(target / "pixi.toml", PIXI_TOML_TEMPLATE)
    write_if_missing(target / ".gitignore", GITIGNORE_TEMPLATE)

    print(
        f"\nDone. Project: {target.resolve()}\n"
        f"Next steps:\n"
        f"  cd {target} && pixi install && pixi run quarto preview"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
