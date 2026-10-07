---
name: local-library
description: Build and navigate a structured local folder of documents (papers, reports, manuals) with an index and per-document summaries, optionally paired with searchable markdown versions. Use when the user wants to organize a collection of PDFs/documents for an agent to search and reference later, asks to "add this paper to my library," asks "do we have anything about [topic]" or to "summarize what's in my library," or wants to search/answer from one that already exists (look for a CLAUDE.md that says "start at INDEX.md"). Starts flat (no topic folders) and only introduces them when the user wants to, or when the library has grown past ~20 unsorted documents.
---

# Local Library

Organizes a folder of documents into a structure an agent (or a human) can navigate without re-reading everything from scratch each time: a root index pointing into optional topic folders, each with short per-document entries (summary, keywords, key results) that let you find the right document before opening it.

**This skill is instructions, not automation.** Classifying a document, summarizing it, and deciding where it belongs are judgment calls, not scriptable steps. The two mechanical pieces (scaffolding a new library, counting documents) have small helper scripts; everything else is you (the agent) reading, writing, and asking.

**The library itself is self-contained, independent of this skill.** Its root `CLAUDE.md` documents the structure directly — layout, filename convention, entry format — so anyone (or any agent) who finds the folder later understands it even without this skill installed. This `SKILL.md` instead covers the *behavior* around maintaining it: when to offer what, how to decide, what to check before acting.

## Structure

```
<library-root>/
  CLAUDE.md                                      # self-contained library docs, generated once - see below
  INDEX.md                                        # current contents: topic folders (if any) + top-level docs
  kalman1960_original_kalman_filter_paper.pdf      # a document not yet assigned to any topic
  kalman1960_original_kalman_filter_paper/          # pdf-to-markdown's own output dir, if converted - see below
    kalman1960_original_kalman_filter_paper.md
    kalman1960_original_kalman_filter_paper_meta.json
    _page_1_Figure_1.jpeg
  optimization/                                       # a topic folder - ONLY exists if the user created one
    INDEX.md                                           # this topic's documents only, same entry format as root
    jones2023_short_description.pdf
    jones2023_short_description/
      jones2023_short_description.md
      jones2023_short_description_meta.json
    classical_methods/                                  # a SUBtopic - background/history for optimization/, not a peer topic
      INDEX.md                                           # same entry format again, just one level deeper
      smith1970_classical_approach.pdf
  bayesian-methods/
    ...
```

Topic folders can themselves contain subtopic folders, same rule, recursively (any directory with its own `INDEX.md`). This is for material that exists specifically *in service of* another topic — e.g. the superseded/historical version of a model that's still actively documented, or foundational background a topic's main documents assume — not for a subject that would stand on its own as a peer topic. See "Nesting: subtopic or sibling topic?" below for how to decide.

`<library-root>` is whatever directory the user is organizing — there's no fixed name (the user's own example used `papers/`, but it's their call, not a requirement).

**Filename convention:** `<author><year>_<short_description_with_underscores>` — e.g. `kalman1960_original_kalman_filter_paper.pdf`. Author surname + publication year, no separator between them, then an underscore and a few words describing the document, spaces replaced with underscores. Apply this consistently when adding a document, even if the source file arrived named something else (`downloaded (3).pdf`, `2301.00001v2.pdf`, etc.) — rename it on the way in.

**Topic folders are opt-in, created by the user, not by you.** A brand-new library starts completely flat: every document lives directly at `<library-root>/`, no topic subfolders. Don't create a topic folder on your own initiative. If the user has already created one (e.g. `optimization/`) and a new or existing document looks like a fit, *offer* it — "this looks like it could go in `optimization/` — want me to file it there, somewhere else, or leave it at the top level?" — and let them decide. Never silently move a document into or out of a topic folder.

**Suggest organizing once it's grown.** Run `python3 scripts/count-docs.py <library-root>` rather than counting by hand or trusting a cached number — it recursively reports top-level, per-topic, and per-subtopic counts (indented by depth), and flags two thresholds: top-level exceeding ~20 (suggest topic folders), and any single topic's *direct* document count exceeding ~50 (suggest splitting that topic into subtopics — see below). Either way: say so and ask, don't wait to be asked, but don't act unprompted either.

## Nesting: subtopic or sibling topic?

When a document (or group of documents) relates to an existing topic, decide whether it belongs *inside* that topic as a subtopic, or *alongside* it as a new sibling topic — same offer-don't-decide rule as topic folders generally, but the judgment call itself:

- **Subtopic** (nest it): the documents exist specifically *in service of* the existing topic, not as an independent subject — e.g. the superseded/historical generation of a model that's still actively maintained under the same name, or foundational background material the topic's main documents assume. Ask something like "these are background for `X/`, not really their own subject — want them nested under it, or should they be a separate topic?"
- **Sibling topic**: the documents would make sense to someone who's never heard of the existing topic — a genuinely independent subject that merely happens to relate to it.
- **A topic outgrowing itself**: if `count-docs.py` flags a topic's direct count past ~50, that's a signal the topic itself may be ready to split into subtopics (e.g. by era, sub-model, or method) — same offer, not an automatic action.

This mirrors the top-level threshold's spirit (flat by default, structure added deliberately, offered not imposed) one level down.

## `CLAUDE.md` vs. topic `INDEX.md`: why only the root auto-loads

Claude Code (and compatible agents) auto-loads `CLAUDE.md` from the working directory *and its ancestors* into context automatically. Since the root `CLAUDE.md` is an ancestor of every topic folder, it gets auto-loaded no matter where in the library you're working — a standing, free entry point. A topic folder's own index doesn't get that same benefit in reverse (auto-loading doesn't reach down into descendants you haven't entered), so naming it `CLAUDE.md` too would buy nothing while suggesting it's a second, independent instructions file. It's just an index, same as the root's — hence `INDEX.md` at every level, with only the root also carrying the self-contained `CLAUDE.md` documentation.

## Setting up a new library

```bash
python3 scripts/init-library.py [path/to/library-root]
```

Defaults to `./local_library` (in the current directory) if no path is given — use that default unless the user names a different location. Creates `CLAUDE.md` (self-contained structural docs — fill in the library's purpose at the top, the rest is generic) and an empty, correctly-structured `INDEX.md` if they don't already exist. Safe to re-run — never overwrites either file once present. If the user already has a `CLAUDE.md`/`INDEX.md` pair that doesn't match this structure, don't force it into this shape; adapt to what's there instead of fighting it.

## Finding existing libraries

Every library root's `CLAUDE.md` starts with a dedicated marker line, `<!-- local-library-root: v1 -->` — an HTML comment, invisible when rendered, kept separate from the human-readable description so it stays greppable even if that wording changes later. Find every local-library instance under a directory tree with:

```bash
rg -l 'local-library-root: v1' --glob CLAUDE.md
```

Use this before assuming no library exists yet, or when the user asks "is there already a library for X" without naming a path.

## Adding a document

1. **Understand it first.** Read enough of the document (title, abstract, skim the structure) to know what it's actually about — don't classify or summarize from the filename alone.
2. **Check for a topic fit.** Read the root `INDEX.md` for existing topic folders. If one looks like a plausible fit, offer it to the user rather than deciding for them (see "Structure" above). If no topic folders exist yet, or the user declines, file the document at the library root — flat is the correct default, not a fallback.
3. **Offer a markdown version, if the tooling's available.** Check whether a PDF-to-markdown capability (e.g. the `pdf-to-markdown` skill) is available in your current session. If so, offer to create one — don't do it automatically, and don't block on it being unavailable; a PDF-only entry is a perfectly valid library member. If accepted, see "Offering a markdown version" below.
4. **Write the entry.** Add one entry for the document to the relevant `INDEX.md` (the topic's, if it has one; otherwise the root `INDEX.md` for top-level documents) — see "Entry format" below.
5. **Update the root `INDEX.md`'s topic list** if you created a new topic folder, so the overview stays accurate.
6. **Check the document-count threshold** via `scripts/count-docs.py` (see "Structure" above) and flag it if crossed.

## Offering a markdown version

If the user accepts, run `pdf-to-markdown` on the document (e.g. `bash scripts/pdf2md.sh kalman1960_original_kalman_filter_paper.pdf`) with the PDF in place at the library root or topic folder where it'll live. No extra file-wrangling needed on top of that — `pdf-to-markdown` already produces a self-contained `<name>/` subdirectory (`<name>.md`, `<name>_meta.json`, and any extracted page images) next to the source PDF, which *is* this library's layout; nothing to rename or merge in. Because each document gets its own subdirectory, there's no cross-document filename collision to worry about even when several documents share a topic folder.

The `<name>_meta.json` file is worth knowing about beyond just being "metadata" — its `table_of_contents` list maps each heading to the 0-indexed PDF page it starts on (`page_id`), which is how you give a precise page citation for something found in the `.md` without re-deriving it by scrolling. See `pdf-to-markdown`'s own `SKILL.md`, "Citing back into the PDF", for the exact mechanics — same file, same technique, just now it's sitting right there in the library structure for reuse. (This is also documented in the library's own `CLAUDE.md`, since it's structural, not skill-specific.)

If you've read `pdf-to-markdown`'s own `SKILL.md`, its "Accuracy" section applies here too — a markdown version in this library is a search aid, not a replacement for the source PDF when something load-bearing needs verifying.

## Entry format

One entry per document, in whichever `INDEX.md` it belongs to (a topic's, or the root's for unassigned top-level documents) — same format either way:

```markdown
### kalman1960_original_kalman_filter_paper — A New Approach to Linear Filtering and Prediction Problems

**Summary:** two to four sentences — what the document is about and why it's here.
**Keywords:** comma, separated, terms, for, matching, a, later, query
**Key results:** the one or two things worth knowing without opening the document
**Files:** [PDF](kalman1960_original_kalman_filter_paper.pdf) · [markdown](kalman1960_original_kalman_filter_paper/kalman1960_original_kalman_filter_paper.md) *(if a markdown version exists)*
```

Keep summaries honest about what you actually read — if you only skimmed the abstract, the summary should reflect that level of confidence, not imply you read the whole document.

## Showing a summary of a library

```bash
python3 scripts/show-library.py [path/to/library-root]
```

Defaults to `./local_library` if no path is given. Prints the library's title (from `CLAUDE.md`), then one entry per document (name, title, `PDF only`/`PDF+md` status, and its `INDEX.md` summary line) grouped by top-level and by topic folder — recursively, so a subtopic nested inside a topic prints indented underneath it, not flattened or missed. A quick "what's in here and is it in good shape" view without reading every `INDEX.md` by hand. It also cross-checks each `INDEX.md` against what's actually on disk and flags two kinds of drift: an indexed entry whose PDF is missing, and a PDF present but not yet in any `INDEX.md`. Use this when the user asks what's in a library, wants a status check, or you suspect an entry and the files on disk have drifted apart (e.g. after a manual `rm` or a half-finished "add a document" step).

## Browsing a library visually with Quarto

For a human (not just an agent) to browse the library's tree structure and read documents in a rendered web page — sidebar navigation mirroring the folder tree, rendered markdown with math/images, and direct links to each PDF — set up a small Quarto site inside the library root:

```bash
python3 scripts/init-quarto.py [path/to/library-root]      # one-time: pixi.toml, _quarto.yml, index.qmd, .gitignore
python3 scripts/sync-quarto-pages.py [path/to/library-root]  # generates/refreshes per-document wrapper pages
cd <library-root> && pixi install && pixi run quarto preview
```

Both scripts default to `./local_library` and are safe to re-run. `init-quarto.py` never overwrites a file that already exists; `sync-quarto-pages.py` regenerates its wrapper pages every run (titles stay in sync with `INDEX.md`) and only rewrites an `INDEX.md` markdown link if it isn't already pointing at the wrapper.

**Why wrapper pages, not rendering the `.md` files directly:** some marker-converted documents start with a literal `---` line (an OCR'd title-page divider), which Quarto/pandoc misreads as a YAML frontmatter delimiter and fails to render. `sync-quarto-pages.py` generates a thin `<name>.qmd` next to each `<name>.md` with real frontmatter (`title:` pulled from the `INDEX.md` entry) that pulls in the original content via `{{< include <name>.md >}}` — the source `.md` files are never modified, and the sidebar gets a proper title instead of a raw filename. `_quarto.yml`'s `project.render` list is scoped to only these `.qmd` files plus the `INDEX.md`/`CLAUDE.md` index pages, so the raw per-document `.md` files are never rendered as standalone pages (avoiding both the YAML bug and duplicate output).

**The sidebar lists `INDEX.md` pages, not individual documents** — each `INDEX.md` already shows its documents with full context (summary/keywords), so the nav only needs to get you to the right index, not enumerate every document. It mirrors the folder tree exactly: a topic with no subtopics is a flat link; a topic *with* subtopics (e.g. one nested under it for historical background — see "Nesting" above) becomes an expandable section whose header is itself a clickable link to that topic's own `INDEX.md`, with its subtopics listed underneath once expanded. `sync-quarto-pages.py` rebuilds this whole sidebar structure from the current folder tree every run, so a newly-nested subtopic folder shows up correctly next time it's run — no manual sidebar editing needed.

Re-run `sync-quarto-pages.py` (then `pixi run quarto render`, or just let a running `quarto preview` pick up the change) whenever a new document gets a markdown conversion — the wrapper won't exist until then, so the `INDEX.md` entry's markdown link stays pointed at the `.md` file as a plain download link in the meantime, same as any `PDF only` entry.

### Undoing the Quarto setup

```bash
python3 scripts/clean-quarto.py [path/to/library-root] [--dry-run]
```

Removes everything `init-quarto.py`/`sync-quarto-pages.py`/`quarto` generated or modified — every `.qmd` wrapper, `pixi.toml`, `_quarto.yml`, `index.qmd`, `styles.css`, `.gitignore`, and the `_site`/`.quarto`/`.pixi` build/cache directories — and reverts `INDEX.md`'s markdown links back from `.qmd` to `.md`, restoring the library to exactly its pre-Quarto state. Never touches document content (`.pdf`, `.md`, images, `_meta.json`). Every file is verified against a content signature before removal, not just matched by filename, so a `pixi.toml`/`.gitignore` that predates the Quarto setup and isn't ours is left alone. Use `--dry-run` first to see what would be removed/reverted without changing anything — and note that dry-run mode must be genuinely side-effect-free; double-check before trusting any variant of this logic if you ever modify it (a prior version of this very script had a bug where `--dry-run` still rewrote the `INDEX.md` links for real).

Useful for checking the full cycle (`init-quarto.py` → `sync-quarto-pages.py` → `quarto render` → `clean-quarto.py` → repeat) still works end-to-end, or just to remove the Quarto site entirely if it's no longer wanted.

## Searching an existing library

1. Start from the library root's `CLAUDE.md` — if it's not already in context (auto-loaded), read it directly, then `INDEX.md`.
2. From `INDEX.md`, identify candidate topic folders or top-level documents for the query.
3. Read the relevant topic `INDEX.md`, if applicable, to narrow down via summaries/keywords/key-results — this should usually be enough to pick the right one or two documents without opening anything else.
4. Read the chosen document's `<name>/<name>.md` (cheaper, searchable) if one exists, falling back to the `.pdf` directly if not.
5. As with any markdown-converted PDF, verify anything load-bearing against the actual PDF before treating it as fact — see `pdf-to-markdown`'s own "Accuracy" section if that skill is available. For a precise page citation, use `<name>/<name>_meta.json`'s `table_of_contents` → `page_id` mapping rather than guessing.
