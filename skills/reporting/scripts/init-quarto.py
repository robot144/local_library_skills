#!/usr/bin/env python3
"""Scaffold a new report/log document from this skill's bundled templates
(templates/report.qmd, templates/log.qmd), and ensure a pixi.toml
providing `quarto` and `jupyter` exists (jupyter is needed for Quarto to
execute the templates' Python code chunks - confirmed by testing: quarto
alone installs fine but fails at render time with "Jupyter is not
available in this Python installation"). Never overwrites an existing
.qmd.

This is this skill's own, fully separate init-quarto.py - not
local-library's. Same name, same ancestor-pixi.toml-search-and-merge
pattern, but no shared file or import between the two: each skill must
keep working if installed alone.

--format pdf also adds `xz` to the pixi manifest and prints a reminder to
run the one-time `quarto install tinytex` step - see PDF_SETUP_NOTE below
for why xz is needed and why the TinyTeX install itself isn't a pixi
dependency, confirmed by testing (see SKILL.md's "PDF output" section).

Usage: python3 init-quarto.py [path/to/name.qmd] [--template report|log] [--format html|pdf]
Defaults to "./report.qmd" (or "./log.qmd" if --template log), format html,
if no path/format is given.
"""
import re
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
DEFAULT_TEMPLATE = "report"
DEFAULT_FORMAT = "html"

DEP_MARKER = "# added by reporting init-quarto.py"
BASE_DEPS = {
    "quarto": ">=1.9,<2",
    "jupyter": ">=1.0,<2",
}
PDF_DEPS = {
    "xz": ">=5.8,<6",  # needed by `tar` for `quarto install tinytex`'s extraction step
}

PDF_SETUP_NOTE = """\
One-time PDF toolchain setup needed before this will render (not a pixi
dependency - Quarto's own TinyTeX, installed outside the pixi environment,
confirmed necessary by testing: conda-forge's texlive-core alone is
missing lualatex and has a broken pdflatex):
  pixi run quarto install tinytex --update-path"""

PIXI_TOML_TEMPLATE = """\
[workspace]
name = "reporting-quarto"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["linux-64"]

[dependencies]
python = ">=3.10,<3.14"
{deps}"""

GITIGNORE_TEMPLATE = """\
.quarto/
*_files/
.pixi/
"""


def write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        print(f"==> {path.name} already exists, leaving it untouched: {path}")
    else:
        path.write_text(content, encoding="utf-8")
        print(f"==> Created {path}")


def merge_deps_into(manifest: Path, deps: dict) -> list:
    """Add any of `deps` missing from an existing pixi.toml. Returns the
    list of dependency names actually added (idempotent - safe to call on
    every run; empty list if everything was already present)."""
    text = manifest.read_text(encoding="utf-8")
    added = []
    for name, spec in deps.items():
        if re.search(rf"^\s*{re.escape(name)}\s*=", text, re.MULTILINE):
            continue
        line = f'{name} = "{spec}"  {DEP_MARKER}'
        if "[dependencies]" in text:
            text = text.replace("[dependencies]", f"[dependencies]\n{line}", 1)
        else:
            text = text.rstrip("\n") + f"\n\n[dependencies]\n{line}\n"
        added.append(name)
    if added:
        manifest.write_text(text, encoding="utf-8")
    return added


def setup_pixi_manifest(start_dir: Path, deps: dict) -> Path:
    """Return the pixi.toml that will provide `deps`: one already in
    start_dir, or the nearest ancestor manifest (missing deps merged into
    either), or a newly-created one in start_dir. A pre-existing manifest
    is never assumed to already have what's needed just because it exists
    - checked and merged in like any other, confirmed necessary by
    testing (a pixi.toml with no quarto dependency installed fine but
    then failed at render time with "quarto: command not found"; one with
    quarto but no jupyter installed and ran quarto fine but failed
    executing a Python code chunk with "Jupyter is not available")."""

    def use(manifest: Path) -> Path:
        added = merge_deps_into(manifest, deps)
        if added:
            print(f"==> Added {', '.join(added)} to existing manifest: {manifest}")
        else:
            print(f"==> {', '.join(deps)} already present in existing manifest: {manifest}")
        return manifest

    own = start_dir / "pixi.toml"
    if own.is_file():
        return use(own)

    for d in start_dir.parents:
        candidate = d / "pixi.toml"
        if candidate.is_file():
            return use(candidate)

    dep_lines = "\n".join(f'{name} = "{spec}"' for name, spec in deps.items())
    own.write_text(PIXI_TOML_TEMPLATE.format(deps=dep_lines + "\n"), encoding="utf-8")
    print(f"==> Created {own}")
    return own


def main() -> int:
    args = sys.argv[1:]
    template = DEFAULT_TEMPLATE
    if "--template" in args:
        i = args.index("--template")
        template = args[i + 1]
        del args[i:i + 2]

    fmt = DEFAULT_FORMAT
    if "--format" in args:
        i = args.index("--format")
        fmt = args[i + 1]
        del args[i:i + 2]
    if fmt not in ("html", "pdf"):
        print(f"error: --format must be 'html' or 'pdf', got '{fmt}'", file=sys.stderr)
        return 1

    template_file = TEMPLATES_DIR / f"{template}.qmd"
    if not template_file.is_file():
        available = sorted(p.stem for p in TEMPLATES_DIR.glob("*.qmd"))
        print(f"error: no such template '{template}' (available: {', '.join(available)})", file=sys.stderr)
        return 1

    target = Path(args[0] if args else f"{template}.qmd")
    if target.exists():
        print(f"==> {target.name} already exists, leaving it untouched: {target}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        content = template_file.read_text(encoding="utf-8")
        if fmt == "pdf":
            content = content.replace("format: html", "format: pdf", 1)
        target.write_text(content, encoding="utf-8")
        print(f"==> Created {target} (from templates/{template}.qmd, format: {fmt})")

    deps = dict(BASE_DEPS)
    if fmt == "pdf":
        deps.update(PDF_DEPS)

    target_dir = target.resolve().parent
    manifest = setup_pixi_manifest(target_dir, deps)
    write_if_missing(target_dir / ".gitignore", GITIGNORE_TEMPLATE)

    print(
        f"\nDone. Document: {target.resolve()}\n"
        f"Quarto environment: {manifest}\n"
        f"Next steps:\n"
        f"  cd {target_dir} && pixi install && pixi run quarto preview {target.name}"
    )
    if fmt == "pdf":
        print(f"\n{PDF_SETUP_NOTE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
