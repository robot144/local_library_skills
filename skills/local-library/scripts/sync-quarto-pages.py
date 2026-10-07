#!/usr/bin/env python3
"""Generate thin Quarto (.qmd) wrapper pages for every document that has a
markdown version, repoint each INDEX.md's "markdown" link at the wrapper,
and rebuild _quarto.yml's sidebar as an explicit flat list (one entry per
document, grouped under a section per topic) instead of Quarto's folder-
based "auto" sidebar.

Why a wrapper instead of rendering the .md directly: some marker-converted
documents start with a literal "---" line (an OCR'd title-page divider),
which Quarto/pandoc misparses as a YAML frontmatter delimiter and fails to
render. The wrapper carries real frontmatter (title: pulled from INDEX.md)
and pulls in the original content via {{< include >}}, untouched - the
source .md files are never modified.

Why an explicit sidebar instead of "contents: auto": each document's .qmd
wrapper lives inside that document's own content subfolder (alongside its
.md, images, and _meta.json - the pdf-to-markdown layout), so Quarto's
auto-sidebar turns every document into its own folder-with-one-page
("Top-level documents" worth of folders, each containing one node named
the same thing). An explicit contents: list flattens that back down to one
sidebar entry per document, grouped under one section per topic folder.
Moving the .qmd up a level instead was tried and rejected - it breaks
image paths, since {{< include >}} does not rewrite relative links.

Usage: python3 sync-quarto-pages.py [path/to/library-root]
Defaults to ./local_library if no path is given. Safe to re-run - wrapper
files are regenerated each time (titles stay in sync with INDEX.md), the
INDEX.md link rewrite is idempotent, and the sidebar is fully rebuilt from
current INDEX.md contents each run.
"""
import re
import sys
from pathlib import Path

import yaml

DEFAULT_ROOT = "local_library"
ENTRY_RE = re.compile(r"^### (?P<name>\S+) — (?P<title>.+)$")
MD_LINK_RE = re.compile(r"\[markdown\]\((?P<name>[^/]+)/(?P=name)\.md\)")
H1_RE = re.compile(r"^# (.+)$", re.MULTILINE)


def yaml_quote(title):
    return title.replace('"', '\\"')


def section_title(index_path):
    text = index_path.read_text(encoding="utf-8")
    m = H1_RE.search(text)
    title = m.group(1).strip() if m else index_path.parent.name
    return re.sub(r" — Topic Index$", "", title)


def write_wrappers_and_fix_links(index_path):
    directory = index_path.parent
    text = index_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    current_name = None
    current_title = None
    changed = False
    out_lines = []

    for line in lines:
        m = ENTRY_RE.match(line)
        if m:
            current_name, current_title = m["name"], m["title"]

        link_m = MD_LINK_RE.search(line)
        if link_m and current_name and link_m["name"] == current_name:
            doc_dir = directory / current_name
            md_file = doc_dir / f"{current_name}.md"
            if md_file.is_file():
                qmd_file = doc_dir / f"{current_name}.qmd"
                qmd_file.write_text(
                    f'---\ntitle: "{yaml_quote(current_title)}"\n---\n\n'
                    f"{{{{< include {current_name}.md >}}}}\n",
                    encoding="utf-8",
                )
                new_line = line[: link_m.start()] + line[link_m.start():link_m.end()].replace(
                    f"{current_name}/{current_name}.md", f"{current_name}/{current_name}.qmd"
                ) + line[link_m.end():]
                if new_line != line:
                    changed = True
                line = new_line

        out_lines.append(line)

    if changed:
        index_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    return changed


def rebuild_sidebar(root, index_files):
    """Sidebar lists only the INDEX.md pages (root + each topic), not every
    individual document - each INDEX.md already shows its documents with
    full context (summary/keywords), so a flat list of entry points into
    those is enough; no need to also enumerate every document in the nav."""
    quarto_yml = root / "_quarto.yml"
    config = yaml.safe_load(quarto_yml.read_text(encoding="utf-8"))

    contents = ["index.qmd"]
    for index_path in index_files:
        prefix = "" if index_path.parent == root else f"{index_path.parent.name}/"
        contents.append({"text": section_title(index_path), "href": f"{prefix}INDEX.md"})

    config.setdefault("website", {}).setdefault("sidebar", {})["contents"] = contents
    config["website"]["sidebar"].pop("auto", None)

    quarto_yml.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True, width=1000),
        encoding="utf-8",
    )


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1
    root = root.resolve()

    index_files = [root / "INDEX.md"]
    index_files += sorted(
        d / "INDEX.md" for d in root.iterdir() if d.is_dir() and (d / "INDEX.md").is_file()
    )
    index_files = [p for p in index_files if p.is_file()]

    total_wrappers = 0
    for index_path in index_files:
        changed = write_wrappers_and_fix_links(index_path)
        n = len(list(index_path.parent.glob("*/*.qmd")))
        print(f"{index_path.relative_to(root.parent)}: {'updated links, ' if changed else ''}wrapper pages present: {n}")
        total_wrappers += n

    if (root / "_quarto.yml").is_file():
        rebuild_sidebar(root, index_files)
        print(f"\nRebuilt sidebar in _quarto.yml ({len(index_files)} sections).")
    else:
        print("\nNo _quarto.yml found - run init-quarto.py first to scaffold the Quarto project.")

    print(f"Done. {total_wrappers} .qmd wrapper pages in place.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
