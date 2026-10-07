#!/usr/bin/env python3
"""Count documents in a local-library, broken down by topic and top-level
(unassigned). A "topic folder" is any subdirectory containing its own
INDEX.md; anything else (e.g. a per-document pdf-to-markdown output
folder like kalman1960_.../) is not a topic and is skipped. Topic folders
may themselves contain subtopic folders (same rule, recursively) - e.g. a
"historical background" subfolder nested under an active topic.

Usage: python3 count-docs.py [path/to/library-root]
Defaults to ./local_library if no path is given.
"""
import sys
from pathlib import Path

THRESHOLD = 20
SUBTOPIC_THRESHOLD = 50
DEFAULT_ROOT = "local_library"


def count_pdfs(directory: Path) -> int:
    return sum(
        1 for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
    )


def subtopics(directory: Path):
    return sorted(
        p for p in directory.iterdir() if p.is_dir() and (p / "INDEX.md").is_file()
    )


def count_topic(directory: Path, depth: int) -> int:
    direct = count_pdfs(directory)
    print(f"{'  ' * depth}{directory.name}/: {direct}")
    if direct > SUBTOPIC_THRESHOLD:
        print(
            f"{'  ' * depth}  NOTE: {direct} documents directly in this topic exceeds "
            f"the ~{SUBTOPIC_THRESHOLD} suggested threshold - consider offering to split "
            "into subtopic folders (see SKILL.md)."
        )
    total = direct
    for sub in subtopics(directory):
        total += count_topic(sub, depth + 1)
    return total


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1

    top_level = count_pdfs(root)
    print(f"Top-level (unassigned): {top_level}")

    total_topic = 0
    for entry in subtopics(root):
        total_topic += count_topic(entry, 1)

    total = top_level + total_topic
    print(f"Total: {total} ({top_level} top-level, {total_topic} in topics)")

    if top_level > THRESHOLD:
        print(
            f"\nNOTE: {top_level} top-level documents exceeds the ~{THRESHOLD} "
            "suggested threshold - consider offering to organize into topics "
            "(see SKILL.md)."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
