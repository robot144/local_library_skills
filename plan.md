# Plan: Widening scope to research skills

## Goal

Widen this repo's scope from a local-document-library toolkit to a broader
set of **research skills** for coding agents — skills that support not just
organizing a folder of documents, but the research work done around it.

What exactly that includes is still being scoped out; this file will grow
into a fuller roadmap as that's decided.

## Status

**Existing skills (shipped, working):**

| Skill | Purpose |
|---|---|
| `pdf-to-markdown` | Convert a PDF into searchable markdown via local OCR (marker-pdf). |
| `local-library` | Organize a folder of documents into an indexed, searchable structure, with optional Quarto browsing site. |
| `workflow` | Scaffold and extend reproducible research workflows using [Snakemake](https://snakemake.github.io/). First version implemented — see [`workflow_design.md`](workflow_design.md) for the design and [`skills/workflow/SKILL.md`](skills/workflow/SKILL.md) for the skill itself. |
| `reporting` | Author and render one-off research documents (reports, ongoing-work logs) using [Quarto](https://quarto.org/) — domain-agnostic, standalone. First version implemented — see [`reporting_design.md`](reporting_design.md) for the design and [`skills/reporting/SKILL.md`](skills/reporting/SKILL.md) for the skill itself. |

## Testing

Two different problems, two different approaches — see the discussion in
conversation for the reasoning:

- **The scripts** (deterministic Python, e.g. `init-workflow.py`,
  `find-docs.py`): pytest unit tests, under `tests/<skill-name>/`, run via
  `pixi run test`. Covers the pure parsing/scaffolding/cleanup logic —
  **not** actual `pixi install`/`quarto render`/`snakemake` execution,
  which stays a separate, heavier integration concern. 147 tests across
  `workflow`, `reporting`, and `local-library`'s six scripts (started with
  the first two, where this session's real bugs were found, then extended
  to `local-library`). Writing `local-library`'s tests surfaced, and this
  then fixed, one more real bug: `sync-quarto-pages.py`'s docstring claims
  wrapper `.qmd` files are "regenerated each time," but once an
  `INDEX.md` entry's link had been converted to `.qmd`, a later run never
  revisited it — a deleted wrapper never came back, and an edited title
  never resynced. Fixed by matching already-`.qmd` links too (not just
  `.md`), so the wrapper regenerates whenever the source `.md` exists,
  independent of which link suffix is currently in `INDEX.md`; confirmed
  both by a standalone repro script and two pytest regression tests
  (`test_write_wrappers_recreates_missing_wrapper_on_rerun`,
  `test_write_wrappers_resyncs_title_after_index_md_edit`). `pdf-to-markdown`
  remains uncovered — its scripts lean more on actually invoking
  `marker-pdf`/`llama.cpp`, a heavier integration-test shape than the others.
- **The skills themselves** (the `SKILL.md` prose that guides agent
  behavior): no unit-test equivalent exists for natural-language guidance.
  What's actually been validating these so far is manual, in-session
  scenario testing — scaffold, run, inspect the real result — which is how
  every real bug this session was actually found (missing `jupyter`,
  silently-blank HTML titles, `find-docs.py` matching its own templates,
  `clean-docs.py --all`'s unscoped deletion risk, `texlive-core` being
  insufficient for PDF). Formalizing this further (e.g. periodic
  zero-context fresh-agent scenario runs) is a future option, not started.

## Open questions

- `reporting`: reference-in-place vs. copy-in for external data; whether
  Quarto's built-in TOC actually satisfies "control panel" once there's
  real usage to judge it against; living/re-rendered report mode remains
  deferred (PDF output, previously deferred here too, is now implemented —
  see Status above). See [`reporting_design.md`](reporting_design.md)'s
  own Open Questions for detail.
- Whether the current repo architecture (agent-agnostic `skills/<name>/SKILL.md`
  convention, `gh skill install` + manual copy) stays as-is or needs
  reconsidering for the wider scope.
