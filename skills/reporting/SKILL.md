---
name: reporting
description: Author and render one-off research documents (reports, ongoing-work logs) or multi-page documentation sites using Quarto — domain-agnostic, standalone. Use when the user wants to "write a report on X," "start a log of this work," "summarize my progress in a log," "create a report from these results," "set up docs for this project," mentions Quarto directly, or wants a readable narrative document (not raw data) built from a workflow's outputs or a local-library document. Not needed for a quick chat answer that doesn't need its own standing document.
---

# Reporting (Quarto)

Scaffolds and renders one-off, narrative [Quarto](https://quarto.org/)
content from a small set of templates, in two different shapes:

- **documents** — `report`, `log`, and `slides` for now, more later: one
  `.qmd` file is "the document."
- **projects** — `docs` so far, `book` a likely future addition: a whole
  directory is the unit, with no single file that is "the document."

Designed iteratively and reused/refined over time rather than invented
fresh each time, for both shapes.

**This skill is mostly instructions, not automation**, same split as
`workflow`/`local-library`: the mechanical pieces (scaffolding a new
document, finding existing ones, cleaning up render output) have small
helper scripts; choosing a template, deciding what story a report tells,
and referencing external data are judgment calls, documented as
instructions below.

**Independent of `workflow` and `local-library`.** Works with either,
neither, or both — a report will often end up consuming a `workflow`'s
`outputs/` or a `local-library` document as its data/source, but this
skill doesn't depend on either one's files to function.

## Templates

Document templates are bundled at `templates/<kind>.qmd`; project
templates are a whole bundled directory, `templates/<kind>/`. Either way,
copied into place when scaffolding — the generated document/project and
the bundled template are independent afterward (editing one doesn't
touch the other).

**Designed iteratively, on purpose.** If a generated document's skeleton
keeps needing the same manual fix-up across several real uses, that's a
signal to revise the *template* in `templates/`, not just patch the one
document in front of you.

### Document kinds

- **`report`** (default) — a draft skeleton, not a mandate: `Summary`,
  `Introduction`, `Methods`, `Results`, `Discussion`, `Conclusions` as H2
  sections, plus a `data_path` placeholder in the first code chunk.
  Sections are fully user-controlled — offer this as a starting point and
  expect to add, remove, rename, or reorder freely for what the specific
  report actually needs.
- **`log`** — a running record of ongoing work: one H2 section per time
  block, each holding a list of entries. **Default time block is one
  day** — the user may overrule this (e.g. weekly) when daily doesn't fit.
- **`slides`** — a reveal.js presentation skeleton (`format: revealjs`):
  a title slide, a smaller-text slide for dense content, a two-column
  slide, a code slide, and a closing summary slide, each with a `##`
  per slide (Quarto's reveal.js convention) and a `. . .` example for
  click-to-reveal pacing. Extracted from a real presentation's
  structure, not its content — fill in placeholders rather than
  treating the slide count/order as fixed. No `logo:` by default (left
  commented out) since a generic template can't assume a logo asset
  exists; uncomment and point it at a real image once there is one.
  **`--format pdf` isn't supported for this template** — revealjs has
  its own export workflow (render to HTML, then the browser's Print to
  PDF), not Quarto's html/pdf toggle.

`report` and `log` use Quarto's own built-in table of contents
(`toc: true`, `toc-depth: 2`) as the navigation "control panel" — a
floating panel listing every section and subsection, native to Quarto's
HTML output, nothing custom to build for a first version. `slides`
doesn't — reveal.js has its own slide-number/menu navigation instead.

### Project kinds

- **`docs`** — a multi-page Quarto *website* (`project: type: website`
  in `_quarto.yml`): a navbar (Home, Installation), a floating sidebar
  ("Getting started" section grouping `index.qmd`+`installation.qmd`,
  plus standalone `design.md` and `reference.md` pages), and a
  `figures/` folder. Extracted from a real multi-page docs site's
  *structure*, not its content — same "fill in placeholders, don't treat
  the page set as fixed" stance as `slides`. Split `reference.md` into
  several pages under their own sidebar section once there's enough
  reference material to need it; don't pre-split before that.
  **`book`** (Quarto's `project: type: book`) is a likely future second
  project kind — architecturally identical to `docs` (same whole-project
  shape, chapters instead of sidebar sections) — not built yet since
  nothing has needed it so far.

## Setting up a new document

```bash
python3 scripts/init-quarto.py [path/to/name.qmd] [--template report|log|slides] [--format html|pdf]
```

Defaults to `--template report`, `--format html`, and `./report.qmd` (or
`./<template>.qmd` for any other `--template`) with no path given — see
"PDF output" below for what `--format pdf` adds (not supported for
`--template slides` — see "Templates" above). Copies the chosen template into
place, and ensures a `pixi.toml` providing `quarto`+`jupyter` exists —
searching upward for an ancestor manifest and merging the dependencies
in, same pattern `local-library`'s own `init-quarto.py` uses, but a
**fully separate script with no shared file or import between the two
skills**. Never overwrites an existing `.qmd`.

**Always prefers merging into whatever `pixi.toml` already governs the
project — never creates a nested one if an ancestor manifest exists.**
Opposite of `workflow`'s stance (which insists on a self-contained,
nested manifest per workflow) on purpose: a workflow is one substantial
thing that should survive being copied elsewhere, but reports/logs are
usually many small documents in the same project that should share one
environment, not each carry a near-identical manifest of their own.

**Fill in the title/author placeholders and the `data_path` cell right
after scaffolding** — don't leave `[Report title]`/`[Author]` or
`path/to/your/data` sitting in a document that's actually going to be
used.

## Setting up a new documentation project

```bash
python3 scripts/init-docs.py [path/to/project-dir] [--template docs]
```

Defaults to `--template docs` and `./docs` with no path given. Copies
the chosen *directory* template into place (unlike `init-quarto.py`,
there's no single `.qmd` to copy), and always writes its own,
self-contained `pixi.toml` providing `quarto`+`jupyter` — **never**
merged into an ancestor manifest, the opposite of `init-quarto.py`'s
default and the same stance `workflow` takes, since a docs site is a
substantial, long-lived thing meant to stand on its own, not a quick
one-off sharing an environment with whatever else is in the same parent
project. Never overwrites an existing project — if the target directory
already has a `_quarto.yml`, it's left untouched.

**Fill in the title placeholder and every page's content right after
scaffolding** — same "don't leave placeholders in a real document"
discipline as single documents, just across more files (`_quarto.yml`'s
`website.title`, plus `index.qmd`/`installation.qmd`/`design.md`/
`reference.md`).

## Referencing external data

Point the report's first code chunk (`data_path` in the `report`
template) at whatever it's actually about — a `workflow`'s `outputs/`, a
`local-library` document, anything else — and have every later chunk
reference that variable rather than hardcoding paths scattered through
the document. Makes it obvious, when revisiting a report later, what it
was actually built from. Reference data in place by default rather than
copying it into the report's own folder — reports are usually written
close in time to whatever they're reporting on, so staleness from
referencing in place is a minor risk; copying is something to offer
specifically for a report meant to outlive or travel separately from its
source.

## Finding documents created by this skill

Every document this skill scaffolds carries two fields in its own YAML
frontmatter (not an HTML-comment marker — a `.qmd` already has
frontmatter, so use it properly):

```yaml
reporting-skill-doc: v1
reporting-skill-kind: report   # or log, slides   (article still later)
```

```bash
python3 scripts/find-docs.py [path/to/search-root]
```

Defaults to `.` — unlike `init-quarto.py`, there's no single fixed root to
default into, since documents made by this skill can live anywhere (next
to the workflow they report on, in an ad-hoc `reports/` folder, wherever).
Recursively finds every marked `.qmd`, and prints a listing grouped by
kind with each document's title, date, and ready-to-paste preview command.
Skips any `templates/*.qmd` — confirmed necessary by testing, since this
skill's own bundled templates carry the same marker every document
scaffolded from them inherits, and showed up indistinguishable from a
real document before this exclusion. (Known limitation: a user's own
folder genuinely named `templates/` containing real documents would also
get skipped — an acceptable tradeoff for now, not revisited unless it
actually bites someone.)
Use this before assuming no report/log exists yet, or when the user asks
"is there already a log for X" without naming a path.

## Cleaning up

```bash
python3 scripts/clean-docs.py [path/to/search-root]          # <name>.html + <name>.pdf + <name>_files/ for every marked doc
python3 scripts/clean-docs.py [path/to/search-root] --all      # also .quarto/ and .pixi/ local to a doc's own folder
python3 scripts/clean-docs.py [path/to/search-root] --dry-run    # report only, change nothing
```

Defaults to `.`. Removes only Quarto's *render output* for documents
carrying this skill's marker (`<name>.html`, `<name>.pdf`, `<name>_files/`)
— never the `.qmd` source itself. Checks both output formats regardless
of a document's own `format:` frontmatter, since `quarto render --to pdf`
can produce a PDF one-off without changing it — confirmed by testing: an
earlier version only checked `.html` and missed a `.pdf` generated this
way. Same marker-scoping and `templates/` exclusion as `find-docs.py`, so
it never touches a Quarto artifact unrelated to this skill.

**`--all`'s `.quarto/`/`.pixi/` cleanup is scoped to a document's own
directory only — never a blanket search of the whole tree.** Confirmed
necessary by testing: an unscoped search, run from a repository root,
found (and would have deleted) other projects' and the repository's own
shared `.pixi/` environments, none of which belonged to a reporting-skill
document. If a document's `pixi.toml` actually lives in an ancestor
directory (the usual case — see `init-quarto.py`'s ancestor-merge
behavior above), `--all` won't reach it there; that's intentional, since
an ancestor manifest is shared infrastructure, not something one document
owns.

## Authoring

Ask what story the document needs to tell before writing it — don't just
dump every available number/figure into a report, and don't pad a log
with filler entries. Same "judgment call, not scriptable" stance
`local-library` takes with its own document summaries.

## Rendering

```bash
quarto render <name>.qmd      # regenerates <name>.html (+ <name>_files/ assets)
quarto preview <name>.qmd       # live preview while editing
```

No dry-run-style discipline needed the way `workflow` has — rendering a
report isn't an expensive or destructive operation the way running a
model is.

**Always show the full preview command, not an abbreviated pointer** —
whenever this skill creates or summarizes a document, in conversation and
not just the scripts' own output, give the actual `cd <dir> && pixi
install && pixi run quarto preview <name>.qmd`, not "now run quarto
preview" left for the user to complete themselves.

### PDF output

```bash
python3 scripts/init-quarto.py [path/to/name.qmd] [--template report|log] [--format html|pdf]
```

`--format` defaults to `html`. With `--format pdf`, `init-quarto.py` sets
`format: pdf` in the scaffolded document's frontmatter, adds `xz` to the
pixi manifest alongside `quarto`/`jupyter`, and prints a one-time setup
reminder — it does **not** auto-run the install, same "surface the
command, don't run it for the user" stance as rendering itself:

```bash
pixi run quarto install tinytex --update-path
```

**This is Quarto's own TinyTeX, not a pixi dependency** — it installs
outside the pixi-managed environment (e.g. `~/.TinyTeX`), untracked by
`pixi.lock`, and auto-fetches whatever LaTeX packages a given document
needs the first time it's rendered. This was a deliberate choice after
testing the alternative: conda-forge's `texlive-core` package is
genuinely insufficient on its own — it ships neither `lualatex` (Quarto's
default PDF engine) nor working `pdflatex` support (its `mktexfmt` is
missing Perl scripts it needs), and the fix (the full `texlive`
meta-package) is multi-GB. TinyTeX, by contrast, installed cleanly and
rendered correctly — equations, code chunks, and the table of contents
all came out right — once one real blocker was fixed: **in a sandboxed
container, `quarto install tinytex`'s extraction step fails outright
without `xz` on `PATH`** (`tar (child): xz: Cannot exec`), so `xz` *is* a
real `pixi.toml` dependency even though TinyTeX itself isn't — confirmed
by testing both the fresh-manifest and ancestor-merge paths end-to-end,
install through actual PDF render.
