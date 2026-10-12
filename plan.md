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

**Planned extensions (scoping in progress):**

| Skill | Purpose |
|---|---|
| `reporting` (working name) | Build research reports/documents from a workflow's outputs using [Quarto](https://quarto.org/). |

## Open questions

- `reporting` (Quarto): how this relates to `local-library`'s existing, more
  limited Quarto browsing site (`init-quarto.py`/`sync-quarto-pages.py`) —
  same mechanism reused/extended, or a separate, report-focused setup; what
  "a report" means here (one-off writeup vs. a living, re-rendered document
  tied to workflow outputs).
- Whether the current repo architecture (agent-agnostic `skills/<name>/SKILL.md`
  convention, `gh skill install` + manual copy) stays as-is or needs
  reconsidering for the wider scope.
