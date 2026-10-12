#!/usr/bin/env python3
"""Remove Quarto render artifacts (<name>.html, <name>.pdf, <name>_files/)
for every document this skill created (carrying reporting-skill-doc: v1
in its frontmatter) under a directory tree. Never touches the .qmd source
itself - only what `quarto render` produces from it. Both output formats
are checked regardless of a document's own `format:` frontmatter value,
since `quarto render --to <format>` can produce either one-off without
changing it - confirmed by testing: rendering a format:-html document to
PDF via --to pdf left a .pdf file this script would otherwise have missed.

With --all, also removes any .quarto/ (Quarto's own render cache) and
.pixi/ (the installed pixi environment) sitting in the same directory as
one of this skill's own documents - heavier, since removing .pixi/ means
the next render needs a full `pixi install` again, not just a few seconds
of re-rendering. Deliberately NOT a blanket search of the whole tree for
any .quarto/.pixi - confirmed necessary by testing: run from a repository
root, an unscoped search found (and would have deleted) other projects'
and the repository's own shared .pixi/ environments, none of which belong
to a reporting-skill document at all. If a document's pixi.toml actually
lives in an ancestor directory (the usual case - see init-quarto.py's
ancestor-merge behavior), --all won't reach it; that's intentional, since
an ancestor manifest is shared infrastructure, not something owned by one
document.

Scoped to this skill's own marked documents only, same as find-docs.py -
not a blanket "delete every .html under this tree," which could remove
Quarto output belonging to something else entirely.

Usage: python3 clean-docs.py [path/to/search-root] [--all] [--dry-run]
Defaults to "." if no path is given. --dry-run reports what would be
removed without changing anything.
"""
import re
import shutil
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*\n", re.DOTALL)
KV_RE = re.compile(r'^([A-Za-z][\w-]*):\s*(.*)$')
EXCLUDED_DIRS = {".quarto", ".pixi", ".git", ".snakemake", "templates"}


def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fields = {}
    for line in m.group(1).splitlines():
        km = KV_RE.match(line)
        if km:
            fields[km.group(1)] = km.group(2).strip().strip("\"'")
    return fields


def find_docs(root: Path):
    docs = []
    for qmd in sorted(root.rglob("*.qmd")):
        if not EXCLUDED_DIRS.isdisjoint(qmd.relative_to(root).parts):
            continue
        fields = parse_frontmatter(qmd.read_text(encoding="utf-8"))
        if fields.get("reporting-skill-doc") == "v1":
            docs.append(qmd)
    return docs


def remove(path: Path, dry_run: bool, removed: list) -> None:
    removed.append(path)
    if dry_run:
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    clean_all = "--all" in args
    args = [a for a in args if a not in ("--dry-run", "--all")]
    root = Path(args[0] if args else ".").resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1

    docs = find_docs(root)
    removed = []
    for qmd in docs:
        for suffix in (".html", ".pdf"):
            output = qmd.with_suffix(suffix)
            if output.is_file():
                remove(output, dry_run, removed)
        files_dir = qmd.parent / f"{qmd.stem}_files"
        if files_dir.is_dir():
            remove(files_dir, dry_run, removed)

    if clean_all:
        doc_dirs = {qmd.parent for qmd in docs}
        for d in doc_dirs:
            for name in (".quarto", ".pixi"):
                candidate = d / name
                if candidate.is_dir():
                    remove(candidate, dry_run, removed)

    label = "Would remove" if dry_run else "Removed"
    if not removed:
        print("Nothing to clean.")
    else:
        for path in sorted(set(removed)):
            print(f"{label}: {path.relative_to(root.parent)}")

    if clean_all:
        print(
            "\nNote: --all also removes .pixi/ - the next render will need "
            "`pixi install` again, not just a quick re-render."
        )

    tag = "Dry run - nothing changed" if dry_run else "Done"
    print(f"\n{tag}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
