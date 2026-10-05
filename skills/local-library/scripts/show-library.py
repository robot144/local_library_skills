#!/usr/bin/env python3
"""Summarize a local-library: one line per document (title + status) plus a
cross-check between INDEX.md entries and the PDFs actually on disk.

Usage: python3 show-library.py [path/to/library-root]
Defaults to ./local_library if no path is given.
"""
import re
import sys
from pathlib import Path

DEFAULT_ROOT = "local_library"
ENTRY_RE = re.compile(r"^### (?P<name>\S+) — (?P<title>.+)$")
SUMMARY_RE = re.compile(r"^\*\*Summary:\*\*\s*(?P<text>.+)$")


def parse_index(index_path):
    entries = []
    current = None
    for line in index_path.read_text(encoding="utf-8").splitlines():
        m = ENTRY_RE.match(line)
        if m:
            current = {"name": m["name"], "title": m["title"], "summary": ""}
            entries.append(current)
            continue
        if current is not None:
            m = SUMMARY_RE.match(line)
            if m:
                current["summary"] = m["text"]
    return entries


def truncate(text, width=140):
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def describe_dir(directory, label, lines):
    index_path = directory / "INDEX.md"
    entries = parse_index(index_path) if index_path.is_file() else []
    pdfs_on_disk = {
        p.stem for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
    }
    indexed_names = {e["name"] for e in entries}

    lines.append(f"{label} ({len(entries)} indexed, {len(pdfs_on_disk)} PDFs on disk)")
    for e in sorted(entries, key=lambda e: e["name"]):
        pdf_ok = (directory / f"{e['name']}.pdf").is_file()
        md_ok = (directory / e["name"] / f"{e['name']}.md").is_file()
        status = ("PDF+md" if md_ok else "PDF only") if pdf_ok else "MISSING PDF"
        lines.append(f"  - {e['name']} [{status}] — {e['title']}")
        if e["summary"]:
            lines.append(f"      {truncate(e['summary'])}")

    missing = indexed_names - pdfs_on_disk
    orphans = pdfs_on_disk - indexed_names
    if missing:
        lines.append(f"  ! indexed but PDF missing on disk: {', '.join(sorted(missing))}")
    if orphans:
        lines.append(f"  ! PDF on disk but not in INDEX.md: {', '.join(sorted(orphans))}")
    lines.append("")
    return len(entries), len(missing), len(orphans)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1

    title = None
    claude_md = root / "CLAUDE.md"
    if claude_md.is_file():
        for line in claude_md.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

    lines = [f"Library: {title or '(no CLAUDE.md title found)'}", f"Root: {root.resolve()}", ""]

    total_entries, total_missing, total_orphans = describe_dir(root, "Top-level documents", lines)

    topic_dirs = [d for d in sorted(root.iterdir()) if d.is_dir() and (d / "INDEX.md").is_file()]
    for topic in topic_dirs:
        n, m, o = describe_dir(topic, f"Topic: {topic.name}/", lines)
        total_entries += n
        total_missing += m
        total_orphans += o

    if not topic_dirs:
        lines.append("Topics: none yet (library is flat)")
        lines.append("")

    print("\n".join(lines).rstrip())
    print()
    print(f"Total indexed documents: {total_entries} ({len(topic_dirs)} topic folder(s))")
    if total_missing or total_orphans:
        print(
            f"Status: {total_missing} missing-PDF entries, {total_orphans} unindexed "
            "PDFs — see '!' lines above"
        )
    else:
        print("Status: all indexed entries have a PDF on disk, no unindexed PDFs found")

    return 0


if __name__ == "__main__":
    sys.exit(main())
