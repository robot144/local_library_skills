#!/usr/bin/env python3
"""Generate thin Quarto (.qmd) wrapper pages for every document that has a
markdown version, repoint each INDEX.md's "markdown" link at the wrapper,
and rebuild _quarto.yml's sidebar to match the library's folder tree - one
entry per INDEX.md (root + every topic, at any nesting depth), not one
per document.

Why a wrapper instead of rendering the .md directly: some marker-converted
documents start with a literal "---" line (an OCR'd title-page divider),
which Quarto/pandoc misparses as a YAML frontmatter delimiter and fails to
render. The wrapper carries real frontmatter (title: pulled from INDEX.md)
and pulls in the original content via {{< include >}}, untouched - the
source .md files are never modified.

Why an explicit sidebar instead of "contents: auto": each document's .qmd
wrapper lives inside that document's own content subfolder (alongside its
.md, images, and _meta.json - the pdf-to-markdown layout), so Quarto's
auto-sidebar turns every document into its own folder-with-one-page.
Building the sidebar explicitly from INDEX.md files instead keeps it at
one entry per topic/subtopic - each INDEX.md already shows its documents
with full context (summary/keywords), so the nav only needs to get you to
the right INDEX.md, not list every document. Moving the .qmd up a level
instead was tried and rejected - it breaks image paths, since
{{< include >}} does not rewrite relative links.

Nesting: a topic folder may itself contain subtopic folders (same rule,
recursively - any directory with its own INDEX.md). A topic with no
subtopics renders as a flat sidebar link; a topic with subtopics renders
as an expandable section (clickable header via href, plus nested contents
for each subtopic) so the hierarchy is visible in the sidebar itself.

Usage: python3 sync-quarto-pages.py [path/to/library-root]
Defaults to ./local_library if no path is given. Safe to re-run - wrapper
files are regenerated each time (titles stay in sync with INDEX.md), the
INDEX.md link rewrite is idempotent, and the sidebar is fully rebuilt from
the current folder tree each run.
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


def subtopic_index_files(directory):
    return sorted(
        p / "INDEX.md" for p in directory.iterdir()
        if p.is_dir() and (p / "INDEX.md").is_file()
    )


def all_index_files(root):
    result = [root / "INDEX.md"]

    def walk(directory):
        for idx in subtopic_index_files(directory):
            result.append(idx)
            walk(idx.parent)

    walk(root)
    return [p for p in result if p.is_file()]


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


def sidebar_node(index_path, root):
    rel_dir = index_path.parent.relative_to(root)
    prefix = "" if str(rel_dir) == "." else f"{rel_dir}/"
    href = f"{prefix}INDEX.md"
    title = section_title(index_path)

    children = subtopic_index_files(index_path.parent)
    if not children:
        return {"text": title, "href": href}
    return {
        "section": title,
        "href": href,
        "contents": [sidebar_node(child, root) for child in children],
    }


def rebuild_sidebar(root):
    quarto_yml = root / "_quarto.yml"
    config = yaml.safe_load(quarto_yml.read_text(encoding="utf-8"))

    contents = ["index.qmd", {"text": section_title(root / "INDEX.md"), "href": "INDEX.md"}]
    for child in subtopic_index_files(root):
        contents.append(sidebar_node(child, root))

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

    index_files = all_index_files(root)

    total_wrappers = 0
    for index_path in index_files:
        changed = write_wrappers_and_fix_links(index_path)
        n = len(list(index_path.parent.glob("*/*.qmd")))
        print(f"{index_path.relative_to(root.parent)}: {'updated links, ' if changed else ''}wrapper pages present: {n}")
        total_wrappers += n

    if (root / "_quarto.yml").is_file():
        rebuild_sidebar(root)
        print(f"\nRebuilt sidebar in _quarto.yml ({len(index_files)} INDEX.md pages found).")
    else:
        print("\nNo _quarto.yml found - run init-quarto.py first to scaffold the Quarto project.")

    print(f"Done. {total_wrappers} .qmd wrapper pages in place.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
