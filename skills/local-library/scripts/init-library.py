#!/usr/bin/env python3
"""Scaffold a new local-library root: CLAUDE.md (self-contained structural docs)
+ INDEX.md (current contents). Never overwrites either file if it already exists.

Usage: python3 init-library.py [path/to/library-root]
Defaults to ./local_library if no path is given.
"""
import sys
from pathlib import Path

DEFAULT_ROOT = "local_library"

CLAUDE_MD_TEMPLATE = """\
<!-- local-library-root: v1 -->
# <Describe what this library collects here>

This is a local-library document collection: PDFs, optionally paired with
markdown versions for searching, organized for reference without any
external service. Start at INDEX.md for the current contents.

## Structure

- Documents start flat, directly in this directory: `<name>.pdf`, optionally
  with a `<name>/` subdirectory holding `<name>.md`, `<name>_meta.json`, and
  any extracted page images (produced by converting the PDF to markdown).
- Topic folders (e.g. `optimization/`) are optional, created deliberately
  rather than automatically. Each has its own `INDEX.md` listing just that
  topic's documents, in the same entry format as the root `INDEX.md`.
- A topic folder may itself contain subtopic folders (same rule, recursively)
  — e.g. a historical-background subfolder nested under the topic for the
  model/subject it's background for, rather than listed as an independent
  peer topic. Use this when documents exist specifically in service of
  another topic, not when they'd stand on their own.
- Filenames follow `<author><year>_<short_description_with_underscores>`,
  e.g. `kalman1960_original_kalman_filter_paper.pdf`.

## Browsing with Quarto (optional)

This library may have a small Quarto browsing site set up alongside the
documents: `pixi.toml`, `_quarto.yml`, `index.qmd`, `styles.css`, plus a
`<name>.qmd` wrapper next to each converted document's `<name>.md`. If
those files are present, `cd` into this directory and run `pixi run
quarto preview` to browse the whole tree in a browser — sidebar mirrors
the folder structure, each `INDEX.md` gets its own page. After adding or
converting more documents, regenerate the wrapper pages and sidebar with
the local-library skill's `sync-quarto-pages.py` script.

## Entry format

Each document gets one entry, in its topic's INDEX.md or the root INDEX.md
if unassigned:

### <name> — <Title>

**Summary:** what the document is about and why it's here.
**Keywords:** terms for matching a later query.
**Key results:** the one or two things worth knowing without opening it.
**Files:** [PDF](<name>.pdf) · [markdown](<name>/<name>.md) *(if present)*

## Citing a specific page

If `<name>/<name>_meta.json` exists, its `table_of_contents` list maps each
heading to the (0-indexed) PDF page it starts on via `page_id` - use
`page_id + 1` for a 1-indexed page reference.
"""

INDEX_MD_TEMPLATE = """\
# Library Index

## Topics

_No topic folders yet. Documents start flat, directly in this directory. Create
a topic folder (and list it here) when it's useful, not before - see CLAUDE.md._

## Top-level documents

_Entries for documents not yet assigned to a topic go here, one per document -
see CLAUDE.md for the entry template. Run scripts/count-docs.py to check
current counts rather than maintaining a number here by hand._
"""


def write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        print(f"\n==> {path.name} already exists, leaving it untouched: {path}")
    else:
        path.write_text(content, encoding="utf-8")
        print(f"\n==> Created {path}")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()

    write_if_missing(root / "CLAUDE.md", CLAUDE_MD_TEMPLATE)
    write_if_missing(root / "INDEX.md", INDEX_MD_TEMPLATE)

    print(f"\nDone. Library root: {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
