#!/usr/bin/env python3
"""Remove everything the Quarto browsing-site scripts (init-quarto.py,
sync-quarto-pages.py, quarto itself) generated or modified, restoring the
library to its pre-Quarto state: original PDFs, converted .md files,
images, and INDEX.md/CLAUDE.md with plain .md markdown links - nothing
Quarto-specific left behind. Useful for testing the full init -> sync ->
render -> clean cycle, or just to undo the Quarto setup entirely.

Safety: every file is verified against a content/structure signature
before removal, not just matched by filename - a pixi.toml, .gitignore,
etc. that predates the Quarto setup and isn't ours is left alone. Never
touches document content (.pdf, .md, images, _meta.json). Also sweeps any
stray `*.html` file outside `_site/` - a single-file `quarto render
<file>` within a website project can write output next to the source
instead of into output-dir, so these can show up scattered through the
tree; unconditionally safe to remove since this project never authors
.html content directly.

Usage: python3 clean-quarto.py [path/to/library-root] [--dry-run]
Defaults to ./local_library if no path is given. --dry-run reports what
would be removed/reverted without changing anything.
"""
import re
import shutil
import sys
from pathlib import Path

DEFAULT_ROOT = "local_library"
MD_LINK_QMD_RE = re.compile(r"\[markdown\]\((?P<name>[^/]+)/(?P=name)\.qmd\)")
QUARTO_DEP_LINE_RE = re.compile(r"\n?^.*# added by local-library init-quarto\.py\s*$\n?", re.MULTILINE)


def is_our_pixi_toml(path):
    return path.is_file() and 'name = "local-library-quarto"' in path.read_text(encoding="utf-8")


def strip_merged_quarto_dep(root, dry_run):
    """If init-quarto.py merged the quarto dependency into an ancestor's
    pixi.toml instead of creating a fresh one at the library root (see
    init-quarto.py), surgically remove just that one line - never delete or
    otherwise touch a manifest this library doesn't fully own. Returns the
    manifest path touched, or None."""
    if (root / "pixi.toml").is_file():
        return None  # library has its own manifest - handled by is_our_pixi_toml above
    for d in root.parents:
        candidate = d / "pixi.toml"
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
            new_text, n = QUARTO_DEP_LINE_RE.subn("\n", text, count=1)
            if n and not dry_run:
                candidate.write_text(new_text, encoding="utf-8")
            return candidate if n else None
    return None


def is_our_quarto_yml(path):
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return "type: website" in text and "output-dir: _site" in text


def is_our_index_qmd(path):
    return path.is_file() and "Browse the library structure in the sidebar" in path.read_text(encoding="utf-8")


def is_our_styles_css(path):
    return path.is_file() and ".sidebar-item-text" in path.read_text(encoding="utf-8")


def is_our_gitignore(path):
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return "_site/" in text and ".pixi/" in text and ".quarto/" in text


def is_our_wrapper_qmd(path):
    if not path.is_file() or path.name == "index.qmd":
        return False
    if not path.with_suffix(".md").is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return text.startswith("---\ntitle:") and "{{< include " in text


def revert_index_links(index_path, dry_run):
    text = index_path.read_text(encoding="utf-8")
    new_text, n = MD_LINK_QMD_RE.subn(lambda m: f"[markdown]({m['name']}/{m['name']}.md)", text)
    if n and not dry_run:
        index_path.write_text(new_text, encoding="utf-8")
    return n


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    root = Path(args[0] if args else DEFAULT_ROOT)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1
    root = root.resolve()

    removed = []

    def remove_file(path, check):
        if check(path):
            removed.append(path)
            if not dry_run:
                path.unlink()

    def remove_dir(path):
        if path.is_dir():
            removed.append(path)
            if not dry_run:
                shutil.rmtree(path)

    remove_file(root / "pixi.toml", is_our_pixi_toml)
    merged_manifest = strip_merged_quarto_dep(root, dry_run)
    remove_file(root / "_quarto.yml", is_our_quarto_yml)
    remove_file(root / "index.qmd", is_our_index_qmd)
    remove_file(root / "styles.css", is_our_styles_css)
    remove_file(root / ".gitignore", is_our_gitignore)

    remove_dir(root / "_site")
    remove_dir(root / ".quarto")
    remove_dir(root / ".pixi")

    for qmd in root.rglob("*.qmd"):
        remove_file(qmd, is_our_wrapper_qmd)

    excluded_dirs = {"_site", ".pixi", ".quarto"}
    for html in root.rglob("*.html"):
        if excluded_dirs.isdisjoint(html.relative_to(root).parts):
            remove_file(html, lambda p: True)

    reverted = 0
    for index_md in root.rglob("INDEX.md"):
        reverted += revert_index_links(index_md, dry_run)

    label = "Would remove" if dry_run else "Removed"
    for path in sorted(set(removed)):
        print(f"{label}: {path.relative_to(root.parent)}")

    if merged_manifest:
        verb2 = "Would remove" if dry_run else "Removed"
        print(f"{verb2} merged quarto dependency from: {merged_manifest}")

    verb = "Would revert" if dry_run else "Reverted"
    print(f"{verb} {reverted} .qmd markdown link(s) back to .md in INDEX.md files.")

    tag = "Dry run - nothing changed" if dry_run else "Done"
    print(f"\n{tag}. {len(set(removed))} Quarto-generated path(s) {'would be ' if dry_run else ''}removed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
