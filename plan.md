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

## Open questions

- `reporting`: reference-in-place vs. copy-in for external data; whether
  Quarto's built-in TOC actually satisfies "control panel" once there's
  real usage to judge it against; living/re-rendered report mode and
  non-HTML output formats both explicitly deferred past the first,
  one-off-document version. See [`reporting_design.md`](reporting_design.md)'s
  own Open Questions for detail.
- Whether the current repo architecture (agent-agnostic `skills/<name>/SKILL.md`
  convention, `gh skill install` + manual copy) stays as-is or needs
  reconsidering for the wider scope.
