#!/usr/bin/env python3
"""Find every .qmd document created by this skill (carrying
reporting-skill-doc: v1 in its YAML frontmatter) under a directory tree,
and print a listing grouped by kind (report/log/...), with title, date,
and a ready-to-paste quarto preview command for each.

Lightweight frontmatter parsing (simple "key: value" line scanning
between the two `---` delimiters) - not a full YAML parser, no dependency
beyond the stdlib.

Usage: python3 find-docs.py [path/to/search-root]
Defaults to "." if no path is given (documents made by this skill can be
anywhere - there's no single fixed root the way local-library/workflow
have one).

Excludes this skill's own bundled templates (any `templates/*.qmd`) -
confirmed necessary by testing: they carry the same frontmatter marker
every document scaffolded from them inherits, so without this exclusion
the skill's own source material shows up indistinguishable from a user's
actual report/log.
"""
import re
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
            docs.append((qmd, fields))
    return docs


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1

    docs = find_docs(root)
    if not docs:
        print(f"No reporting-skill documents found under {root}.")
        return 0

    by_kind = {}
    for qmd, fields in docs:
        kind = fields.get("reporting-skill-kind", "(unknown)")
        by_kind.setdefault(kind, []).append((qmd, fields))

    print(f"Reporting-skill documents found under {root}:\n")
    for kind in sorted(by_kind):
        entries = sorted(by_kind[kind], key=lambda e: e[1].get("date", ""))
        print(f"{kind} ({len(entries)}):")
        for qmd, fields in entries:
            title = fields.get("title", "(no title)")
            date = fields.get("date", "(no date)")
            rel = qmd.relative_to(root)
            print(f"  {date}  {title}  [{rel}]")
            print(f"    cd {qmd.parent} && pixi run quarto preview {qmd.name}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
