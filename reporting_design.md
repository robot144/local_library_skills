# Design: `reporting` skill (Quarto)

Status: implemented (first version). See
[`skills/reporting/SKILL.md`](skills/reporting/SKILL.md) for the skill
itself (`init-quarto.py`, `find-docs.py`, `templates/report.qmd`,
`templates/log.qmd`) — this file remains the design record (rationale,
open questions) behind those decisions.

## Purpose

Help an agent author and render one-off, narrative Quarto documents —
reports and, now, ongoing-work logs, scaffolded from a small set of
templates designed iteratively and reused/refined over time, rather than
freshly invented per document. Domain-agnostic, same spirit as `workflow`
and `local-library`: usable standalone, but will often end up consuming a
`workflow`'s `outputs/` or a `local-library` document as its underlying
data/source.

**Scope decisions already made:**
- **Domain-agnostic, standalone.** Not tied to `workflow` or `local-library`
  — works with either, neither, or both installed. Skills in this repo must
  stay independently installable (a user may `gh skill install` just one),
  so this skill cannot depend on either of their files directly.
- **"A report" (and now "a log") means a one-off written document** — a
  narrative Quarto document (text + tables/figures pulled from data),
  authored once (or appended to over time, for a log) rather than a
  living/auto-re-rendered dashboard — that's a plausible future extension
  (see Open Questions), not this skill's first target.
- **Multiple starter templates, not one generic shape.** Scaffolding picks
  from a small, growing set of templates — `report` and `log` for starters,
  `slides` and `article` later — rather than a single one-size-fits-all
  skeleton. See "Templates" below.
- **First output format: HTML only.** No PDF/LaTeX toolchain dependency
  yet.
- **Quarto-reuse stance, revised**: this skill gets its own `init-quarto.py`
  — same name and same *pattern* as `local-library`'s (searching upward for
  an ancestor `pixi.toml` and merging the `quarto` dependency into it,
  rather than always creating a fresh, possibly-shadowing manifest), but a
  **fully separate file with no runtime or import dependency on
  `local-library`'s script**. Each skill must work when installed alone,
  so there's no shared module either could call into — any resemblance
  between the two is by convention (copy the pattern, not the file), not
  because one depends on the other. Worth being explicit about this so a
  later edit doesn't "helpfully" consolidate them into a real dependency
  just because they ended up looking similar.
- **Deliberately the opposite of `workflow`'s manifest stance, for a
  reason.** `workflow` insists on a self-contained, nested `pixi.toml` per
  workflow (explicit `python`, nothing relying on an ancestor) because a
  workflow is one substantial, long-lived thing that should survive being
  copied or orphaned from its parent project. A report or log is the
  opposite: usually one of many small documents in the same project, which
  should share *one* environment rather than each carrying its own
  near-identical manifest. So `init-quarto.py` here always prefers merging
  `quarto`+`jupyter` into whatever `pixi.toml` already governs the
  project (searching upward), and only creates a fresh one if truly
  nothing exists anywhere upward — confirmed by testing: scaffolding two
  documents into the same project correctly merged into the one existing
  root manifest both times, with no nested per-document manifest created.
- **Not the same Quarto project type as `local-library`'s browsing site.**
  That's a `type: website` project (sidebar nav over a folder tree) —
  a fundamentally different artifact from a single narrative report. This
  skill scaffolds a standalone `.qmd` document; no `_quarto.yml` website
  project needed for that.

## Proposed structure

Lighter-weight than `workflow`/`local-library` roots, since a report is
usually one file, not a long-lived structure you keep returning to:

```
<report-location>/
  <name>.qmd              # the report: title/author frontmatter + narrative + code
                             # chunks that load data and render tables/figures
  pixi.toml / pixi.lock      # ensures `quarto` is available - same ancestor-search-
                                # and-merge pattern as local-library's init-quarto.py
  .gitignore                   # .quarto/, <name>_files/ (Quarto's render-output
                                  # assets dir), .pixi/
```

Default execution engine: Python (Jupyter), consistent with this repo's
pixi/Python-first convention — not R/knitr, unless a specific report's data
processing is already in R.

**Resolved** (see "Finding documents created by this skill" below): unlike
`workflow`/`local-library`, no standing root or `CLAUDE.md` is needed here.
Each document carries its own discovery marker in its YAML frontmatter, so
documents can simply live wherever makes sense — next to the workflow they
report on, in an ad-hoc `reports/` folder, wherever — and `find-docs.py`
locates them regardless.

## Templates

**Where they live**: bundled with the skill itself, at
`skills/reporting/templates/<kind>.qmd` — not generated fresh each time,
and not part of any individual report's own folder. Scaffolding *copies*
the chosen template into place; the generated document and the bundled
template are independent afterward (editing one doesn't touch the other).

**Designed iteratively, on purpose.** If a generated document's skeleton
keeps needing the same manual fix-up across several real uses, that's a
signal to revise the *template* in `skills/reporting/templates/`, not just
patch the one document in front of you — the templates are meant to
accumulate improvements the same way this design doc itself has gone
through rounds of revision, not be treated as a frozen starting point.

**Current template kinds:**

- **`report`** (likely default) — a draft skeleton, not a mandate: H2
  sections for `Title`/`Author` (frontmatter, not a body section),
  `Summary`, `Introduction`, `Methods`, `Results`, `Discussion`,
  `Conclusions`. Sections are fully user-controlled — offer this as a
  starting point and expect to add, remove, rename, or reorder freely for
  what the specific report actually needs, same "offer, don't impose"
  stance `local-library` takes with its own topic folders.
- **`log`** — a running record of ongoing work. Structure: one H2 section
  per time block (e.g. `## 2026-10-12`), each containing a list of
  entries for that block. **Default time block is one day** — the user
  may overrule this (e.g. per-week sections for a lower-frequency log)
  when it doesn't fit; the template's default, not a hard rule.

**Planned, not designed yet:**

- **`slides`** — Quarto's `revealjs` format instead of `html`; different
  enough (no continuous body narrative, no shared control-panel/TOC
  navigation model) that it's deferred rather than squeezed in now.
- **`article`** — closer to `report` in shape, but likely different
  formatting conventions (e.g. journal-style single-column layout,
  possibly PDF/LaTeX eventually) — deferred alongside PDF support
  generally.

**Control panel (navigation), simple version**: for `report` and `log`
alike, start with Quarto's own built-in table of contents (`toc: true`,
`toc-depth: 2` in the `.qmd` frontmatter) — a floating panel listing every
section and subsection, native to Quarto's HTML output, nothing bespoke
to build. "Simple for starters" means reaching for what Quarto already
provides before building a custom navigation panel — revisit only if this
doesn't actually satisfy what's wanted once there's a real rendered
document to look at.

## Referencing external data

The central design question this skill actually needs to answer, since
"domain-agnostic standalone" means it can't assume where its data comes
from:

- **Reference in place vs. copy in.** A report's code chunk can read
  directly from an external path (e.g. `../my_workflow/outputs/results.csv`)
  — simplest, but makes the report non-portable if that path moves or the
  workflow's `outputs/` gets reorganized. Copying the needed data into a
  `data/` folder next to the report makes it self-contained but duplicates
  storage and can go stale if the source changes after copying. Likely
  answer: reference in place by default (reports are usually written
  close in time to whatever they're reporting on, so staleness is a minor
  risk), with copying as something to offer for a report meant to outlive
  or travel separately from its source — not decided.
- **A documented convention for the "where's my data" cell**, not
  automation: the report's first code chunk sets a path (or a small number
  of named paths) to whatever it's reporting on, with everything below it
  referencing that variable rather than hardcoded paths scattered through
  the document. Makes it obvious, when revisiting a report later, what it
  was actually built from.

## Finding documents created by this skill

Same motivating idea as `local-library`'s root marker and `workflow`'s
discovery marker, adapted to the fact that this skill's documents are
scattered standalone files, not one thing per root folder — so the marker
goes in each generated `.qmd`'s own YAML frontmatter (a genuine metadata
field, not an HTML comment — unlike `CLAUDE.md`, a `.qmd` already has a
frontmatter block, so use it properly rather than reaching for the
HTML-comment trick that's only needed where no frontmatter exists):

```yaml
---
title: "..."
reporting-skill-doc: v1
reporting-skill-kind: report   # or log, slides, article later
---
```

**`find-docs.py [path/to/search-root]`** — unlike `init-quarto.py`, this
one defaults to `.` (the current directory), not a fixed single root name,
since there's no equivalent of "the library" or "the workflow" to default
into — documents made by this skill can be anywhere. Recursively finds
every `*.qmd` under the search root carrying `reporting-skill-doc: v1`,
reads its `title`, `reporting-skill-kind`, and `date` (if present) straight
out of the frontmatter, and prints a listing grouped by kind — closer to
`local-library`'s `show-library.py` in spirit (a quick "what's here" view)
than to its one-line `rg` discovery command, because there's an actual
listing worth formatting here (title/date/kind), not just a set of root
paths. Lightweight frontmatter parsing (simple key: value line scanning
between the two `---` delimiters), not a full YAML parser — no new
dependency beyond the stdlib, consistent with this repo's other scripts.
**Excludes `templates/*.qmd`** — found by testing: the skill's own bundled
templates carry the same marker every document scaffolded from them
inherits, and without this exclusion showed up indistinguishable from a
real document. Known, accepted limitation: a user's own folder genuinely
named `templates/` with real documents in it would also be skipped.

## Scripted helper (proposed)

Mirroring the other two skills' mechanical/judgment split:

- **`init-quarto.py [path/to/name.qmd] --template <kind> --format
  html|pdf`** — this skill's own, fully separate script (not
  `local-library`'s — see "Quarto-reuse stance, revised" above). Copies
  the chosen bundled template (see "Templates" above) into place —
  title/author frontmatter plus the `reporting-skill-doc`/
  `reporting-skill-kind` marker fields filled in — and ensures a
  `pixi.toml` providing `quarto`+`jupyter` (plus `xz` if `--format pdf`)
  exists via the same ancestor-search-and-merge logic `local-library`'s
  script uses — independently implemented, no shared file or import
  between the two. Idempotent, never overwrites an existing `.qmd`.
  `--format pdf` sets `format: pdf` in the scaffolded document and prints
  (never auto-runs) the one-time TinyTeX setup reminder — see "PDF
  output" in `SKILL.md`. Prints the full, ready-to-paste preview command
  as its last line (not just "now run quarto preview" — the actual `cd
  <dir> && pixi install && pixi run quarto preview <name>.qmd`), same
  "next steps" convention `init-workflow.py` and `local-library`'s
  `init-quarto.py` already use.
- **`find-docs.py [path/to/search-root]`** — see "Finding documents
  created by this skill" above. Each listed document gets its own full
  preview command printed alongside it (`cd <doc's dir> && pixi run quarto
  preview <name>.qmd`) — running from the document's own directory is
  always correct regardless of whether its `pixi.toml` is local or
  inherited from an ancestor, since `pixi run` searches upward from cwd.
- **`clean-docs.py [path/to/search-root] [--all] [--dry-run]`** — removes
  Quarto's render output (`<name>.html`, `<name>.pdf`, `<name>_files/`,
  checking both output formats regardless of a document's own `format:`
  frontmatter, since `--to pdf` can produce a one-off PDF without changing
  it - confirmed by testing, an earlier version only checked `.html`) for
  this skill's own marked documents; never the `.qmd` source. `--all` also
  removes `.quarto/`/`.pixi/`, but **only when they sit in a document's
  own directory** — deliberately not a blanket tree-wide search, confirmed
  necessary by testing: an unscoped version, run from a repository root,
  found (and would have deleted) other projects' and the repository's own
  shared `.pixi/` environments that had nothing to do with any reporting
  document. Same marker-scoping and `templates/` exclusion as
  `find-docs.py`.

## Agent-judgment workflows (sketch, not fleshed out yet)

- **Authoring**: ask what story the report needs to tell before writing
  it — don't just dump every available number/figure into a document.
  Same "judgment call, not scriptable" stance as `local-library`'s
  document summaries.
- **Referencing data**: point the report's data-source cell at whatever
  it's reporting on (a `workflow`'s `outputs/`, a `local-library`
  document, anything else) — see "Referencing external data" above.
- **Rendering**: `quarto render <name>.qmd` regenerates `<name>.html`
  (plus a `<name>_files/` assets dir). No dry-run-style discipline needed
  the way `workflow` has — rendering a report isn't an expensive or
  destructive operation the way running a model is.
- **Always show the full preview command, not an abbreviated pointer.**
  Whenever this skill creates or summarizes a document — in conversation,
  not just the scripts' own output — give the actual, ready-to-paste `cd
  <dir> && pixi install && pixi run quarto preview <name>.qmd`, not "now
  run quarto preview" left for the user to complete themselves. Same
  reasoning as `pdf-to-markdown` surfacing its estimate script's exact
  human-readable line instead of re-deriving a shorter paraphrase.

## Open questions

- **Standing root + discovery marker — resolved, no standing root
  needed.** The marker lives in each document's own frontmatter
  (`reporting-skill-doc`/`reporting-skill-kind`), found via `find-docs.py`
  scanning from wherever — so there's no need for a `workflow`/
  `local-library`-style root-plus-`CLAUDE.md` after all. Documents really
  can just live wherever makes sense.
- **Time-block granularity for `log` — resolved**: defaults to one day
  per section; user can overrule (e.g. weekly) when daily doesn't fit.
  See "Templates" above.
- **Reference-in-place vs. copy-in for data** — not decided, see
  "Referencing external data" above.
- **Will Quarto's built-in TOC actually satisfy "control panel"?** —
  simplest-possible first implementation (`toc: true`, `toc-depth: 2`);
  revisit only if it doesn't match what's wanted once there's a real
  rendered document to look at.
- **Template versioning** — `reporting-skill-doc: v1` marks which *scheme*
  version a document was scaffolded under (for `find-docs.py` to parse
  reliably), but doesn't track which *revision* of a given template
  (`report`, `log`, ...) a specific document came from. Worth it once
  templates have actually been revised a few times and it'd be useful to
  know which existing documents still reflect an older skeleton? Not
  decided — don't build it preemptively.
- **Living/re-rendered report mode** — explicitly deferred. Revisit once
  the one-off case is working, if there's real demand for a report that
  re-renders itself whenever its source `workflow` output changes (closer
  to a dashboard than a writeup at that point).
- **PDF output — resolved, implemented.** `init-quarto.py` now takes
  `--format html|pdf` (default `html`): `pdf` sets `format: pdf` in the
  scaffolded document, adds `xz` to the pixi manifest, and prints (never
  auto-runs) the one-time `pixi run quarto install tinytex --update-path`
  setup reminder. Tested end-to-end through both the ancestor-merge and
  fresh-manifest code paths, install through actual PDF render (equations,
  code chunks, TOC all came out correctly). See `SKILL.md`'s "PDF output"
  section for the full finding, including why conda-forge's `texlive-core`
  was tried first and rejected (missing `lualatex`, broken `pdflatex`
  format-building) and why `xz` had to be added as a real `pixi.toml`
  dependency (TinyTeX's own extraction step fails without it in a
  sandboxed container, even though TinyTeX itself installs outside the
  pixi environment). Other formats (`slides`/`revealjs`, etc.) remain
  fully deferred.
- **Multi-document reports** (a report split across several `.qmd` files,
  e.g. one per section) — not considered yet; first target is a single
  `.qmd`.
