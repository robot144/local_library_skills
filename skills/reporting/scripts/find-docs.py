#!/usr/bin/env python3
"""Find every document or project created by this skill under a
directory tree, and print a listing grouped by kind (report/log/...,
docs/...), with title, date (documents only), and a ready-to-paste quarto
preview command for each.

Two different things get found, since this skill scaffolds two different
shapes (see init-quarto.py vs. init-docs.py):
- single-file **documents** (report/log/slides/...): one .qmd, carrying
  reporting-skill-doc: v1 in its own YAML frontmatter.
- **projects** (docs/...): a whole directory with no single file that is
  "the document" - the marker lives as top-level keys in its _quarto.yml
  instead, confirmed by testing that Quarto accepts (and ignores)
  unrecognized top-level keys there with no warning.

Lightweight parsing throughout (simple "key: value" line scanning) - not
a full YAML parser, no dependency beyond the stdlib.

Usage: python3 find-docs.py [path/to/search-root]
Defaults to "." if no path is given (documents made by this skill can be
anywhere - there's no single fixed root the way local-library/workflow
have one).

Excludes this skill's own bundled templates (any `templates/*.qmd` or
`templates/*/_quarto.yml`) - confirmed necessary by testing: they carry
the same markers every document/project scaffolded from them inherits,
so without this exclusion the skill's own source material shows up
indistinguishable from a user's actual report/log/docs site.
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


def parse_flat_keys(text: str) -> dict:
    """Same "key: value" scan as parse_frontmatter, but over a whole YAML
    file rather than a frontmatter block - fine here since our marker
    keys are always unindented top-level scalars, never legitimately
    reused (indented) elsewhere in a _quarto.yml."""
    fields = {}
    for line in text.splitlines():
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


def find_projects(root: Path):
    projects = []
    for quarto_yml in sorted(root.rglob("_quarto.yml")):
        if not EXCLUDED_DIRS.isdisjoint(quarto_yml.relative_to(root).parts):
            continue
        fields = parse_flat_keys(quarto_yml.read_text(encoding="utf-8"))
        if fields.get("reporting-skill-doc") == "v1":
            title_m = re.search(r'^\s*title:\s*(.+)$', quarto_yml.read_text(encoding="utf-8"), re.MULTILINE)
            title = title_m.group(1).strip().strip("\"'") if title_m else "(no title)"
            projects.append((quarto_yml.parent, fields, title))
    return projects


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1

    docs = find_docs(root)
    projects = find_projects(root)
    if not docs and not projects:
        print(f"No reporting-skill documents or projects found under {root}.")
        return 0

    print(f"Reporting-skill documents and projects found under {root}:\n")

    by_kind = {}
    for qmd, fields in docs:
        kind = fields.get("reporting-skill-kind", "(unknown)")
        by_kind.setdefault(kind, []).append((qmd, fields))

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

    by_kind = {}
    for project_dir, fields, title in projects:
        kind = fields.get("reporting-skill-kind", "(unknown)")
        by_kind.setdefault(kind, []).append((project_dir, title))

    for kind in sorted(by_kind):
        entries = sorted(by_kind[kind], key=lambda e: e[1])
        print(f"{kind} project ({len(entries)}):")
        for project_dir, title in entries:
            rel = project_dir.relative_to(root)
            print(f"  {title}  [{rel}/]")
            print(f"    cd {project_dir} && pixi run quarto preview")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
