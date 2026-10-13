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
| `agent-runner` | Launch a coding agent session (Claude Code only, v1) from a script, with automatic vendor resolution — usable standalone or as a `workflow` pipeline step. First version implemented — see [`agent-runner_design.md`](agent-runner_design.md) for the design (including the "Katrina" and eval-harness worked examples) and [`skills/agent-runner/SKILL.md`](skills/agent-runner/SKILL.md) for the skill itself. |

## Testing

Two different problems, two different approaches — see the discussion in
conversation for the reasoning:

- **The scripts** (deterministic Python, e.g. `init-workflow.py`,
  `find-docs.py`): pytest unit tests, under `tests/<skill-name>/`, run via
  `pixi run test`. Covers the pure parsing/scaffolding/cleanup logic —
  **not** actual `pixi install`/`quarto render`/`snakemake` execution
  (or, for `agent-runner`, actually launching a live agent session), which
  stays a separate, heavier integration concern. 176 tests across
  `workflow`, `reporting`, `local-library`'s six scripts, and
  `agent-runner`'s `run-agent.py` (`subprocess.run` mocked throughout, so
  these never spawn a real nested agent). Writing `local-library`'s tests
  surfaced, and this then fixed, one real bug: `sync-quarto-pages.py`'s
  docstring claims wrapper `.qmd` files are "regenerated each time," but
  once an `INDEX.md` entry's link had been converted to `.qmd`, a later
  run never revisited it — a deleted wrapper never came back, and an
  edited title never resynced. Fixed by matching already-`.qmd` links too
  (not just `.md`); confirmed both by a standalone repro script and two
  pytest regression tests. Writing `agent-runner`'s tests then caught a
  second real bug the same way: a quick real-CLI sanity check (not just
  pytest) showed `write_default_vendor_to_config` crashed with
  `FileNotFoundError` when scaffolding a config into a not-yet-existing
  workflow directory — the parent directory was never created before
  writing. Fixed and pinned with a regression test. `pdf-to-markdown`
  remains uncovered — its scripts lean more on actually invoking
  `marker-pdf`/`llama.cpp`, a heavier integration-test shape than the others.
- **The skills themselves** (the `SKILL.md` prose that guides agent
  behavior): no unit-test equivalent exists for natural-language guidance.
  What's actually been validating these so far is manual, in-session
  scenario testing — scaffold, run, inspect the real result — which is how
  every real bug this session was actually found (missing `jupyter`,
  silently-blank HTML titles, `find-docs.py` matching its own templates,
  `clean-docs.py --all`'s unscoped deletion risk, `texlive-core` being
  insufficient for PDF). Formalizing this further is no longer just a
  design on paper: `agent-runner_design.md`'s "Worked example 2"
  (subject-prompt/judge-prompt eval harness, reusing `workflow`'s split →
  per-case → collect rule shape) is now built and actually run, as
  `example_eval_workflow/` — one real test case, real cost ($0.18 for both
  agent invocations), correct `PASS` verdict. Tracing through the design
  before running it for real also caught a genuine bug: the judge's `cwd`
  is deliberately the same as the subject's, so `run-agent.py`'s own
  transcript write would have silently clobbered the subject's transcript
  the judge needed to inspect — fixed by having the subject back up its
  transcript to a distinct filename first. Still just one test case for
  one trivial prompt pair, not a real test suite yet.

## Open questions

- `agent-runner`: first version implemented (Claude Code only), but most
  of the original tensions remain open past v1 by design — multi-vendor
  adapters, capability discovery, safety/blast-radius when an agent step
  runs unattended inside an automated pipeline, and dedicated credential
  handling. See [`agent-runner_design.md`](agent-runner_design.md)'s "What's
  deliberately not here yet" / "Known tensions" for the full list.
- `reporting`: reference-in-place vs. copy-in for external data; whether
  Quarto's built-in TOC actually satisfies "control panel" once there's
  real usage to judge it against; living/re-rendered report mode remains
  deferred (PDF output, previously deferred here too, is now implemented —
  see Status above). See [`reporting_design.md`](reporting_design.md)'s
  own Open Questions for detail.
- Whether the current repo architecture (agent-agnostic `skills/<name>/SKILL.md`
  convention, `gh skill install` + manual copy) stays as-is or needs
  reconsidering for the wider scope.
