# Design: `workflow` skill (Snakemake)

Status: implemented. See [`skills/workflow/SKILL.md`](skills/workflow/SKILL.md)
for the skill itself (`init-workflow.py`, `clean-workflow.py`,
`summarize-workflow.py`) — this file remains the design record (worked
example, rationale, open questions) behind those decisions.

## Purpose

Help an agent scaffold, extend, and run reproducible research workflows
using [Snakemake](https://snakemake.github.io/) — domain-agnostic, same
spirit as `local-library`: a self-contained folder structure anyone (human
or agent) can understand on its own, plus instructions for the judgment
calls around maintaining it.

**Scope decisions already made:**
- **Domain-agnostic.** Not tied to any particular kind of research task
  (simulation, data processing, document pipelines, etc.) — the skill
  teaches "how to scaffold and extend a Snakemake workflow," full stop.
- **Fully independent of `local-library`.** No wiring between the two. A
  project can have both, but neither assumes the other exists.
- **Scaffolding style mirrors `local-library`'s split**: a small helper
  script for the mechanical, one-time setup; everything else (designing
  rules, wiring dependencies, deciding what's disposable) is agent
  judgment, documented as instructions, not scripted.
- **First use case to get working: scaffolding a brand-new workflow.**
  Wrapping existing ad-hoc scripts and extending an already-existing
  workflow are natural follow-ons — see Open Questions.

## Structural categories

Not a fixed set of folder *names* — a fixed set of *roles*, named for what
they actually hold in a given workflow (`local-library` takes the same
stance on its own root folder name). Four roles, derived from working
through a concrete case (see below) and generalized back out:

- **`data/`** — raw/external input, provided by the user, never produced by
  a rule. Whether it's shared across every case or already split per case,
  and whether it needs a derivation step before use or is ready to consume
  directly, is **not** a property of the data itself — it's an accident of
  how the data arrived, and it only affects which rules exist in the DAG,
  not which folder it lives in. Don't split `data/` into "shared" vs.
  "per-case" subcategories; that distinction doesn't hold up (see worked
  example — bathymetry can arrive as one global file or pre-chunked per
  case, and either way it's just `data/`).
- **`templates/`** — the one category that *is* structurally different: a
  template is always copied wholesale and then modified for a specific
  case, never read-and-derived-from in place. That's a different relationship
  to the workflow than any other input, which is why it's worth its own
  category even though it's also "just input the user provided."
- **`scratch/`** — disposable, per-case working/run directories. Fully
  regenerable from `data/` + `templates/` by rerunning the relevant rules.
  Holds anything heavy that isn't worth keeping once you trust the result:
  staged template copies, the model's own run output, and (per the logs
  discussion below) the model's own raw, huge, internal log files. Safe to
  delete wholesale (`rm -rf scratch/<case>/`) once `outputs/` and `logs/`
  for that case look right — nothing structurally useful is lost by doing
  so, since both of those are already-kept distillations of what was in
  there.
- **`outputs/`** and **`logs/`** are the same pattern applied twice: lean,
  valuable, *kept-forever* distillations of something heavy and disposable
  living in `scratch/`.
  - `outputs/` — the actual results worth keeping (stats, figures,
    aggregates).
  - `logs/` — two things: Snakemake's own per-rule orchestration log (via
    the `log:` directive — always small, catches "did the shell/script
    invocation itself fail") **and**, where relevant, a small summary
    distilled from a model's huge internal log that otherwise lives in
    `scratch/<case>/run/` alongside the rest of that run. The distillation
    (what counts as a "main item" — errors, warnings, convergence info,
    timing) is model-specific judgment, same way summarizing a document in
    `local-library` is — the skill documents the pattern, not the content.

## Worked example: per-cyclone model runs → extreme value statistics

Used throughout design discussion to stress-test the categories above
before generalizing them. Inputs: a folder of per-event cyclone files, a
template model setup to be run once per cyclone, a script producing
per-cyclone figures/stats, and a script computing extreme value statistics
across all cyclones' stats. Models in question don't tolerate multiple runs
sharing one folder — each run needs its own isolated copy of the template.

**Rule chain** (all but the last wildcarded over `{cyclone}`):

1. `extract_bathymetry_chunk` — *only exists in the DAG if bathymetry isn't
   already pre-chunked per cyclone.* Cuts a per-cyclone chunk from a global
   bathymetry dataset in `data/`.
2. `prepare_model_input` — the only rule that knows about templates: copies
   `templates/model/` into `scratch/{cyclone}/run/` and patches in that
   cyclone's forcing + bathymetry chunk. Kept separate from `run_model` so
   that re-running the (expensive) model doesn't force re-staging, and
   vice versa.
3. `run_model` — template-agnostic: just executes the model inside whatever
   `scratch/{cyclone}/run/` already contains. Would work unchanged for a
   future workflow with no template at all. Uses `shell:`, not `script:`
   — it's invoking an external model binary, not custom Python.
4. `summarize_run_log` — distills the model's huge internal log (sitting in
   `scratch/{cyclone}/run/`) down to `logs/{cyclone}/summary.log`.
5. `per_cyclone_stats` — reads `scratch/{cyclone}/run/`, writes
   `outputs/{cyclone}/stats.csv` + figures. Uses `script:`.
6. `extreme_value_stats` — aggregates `outputs/*/stats.csv` across *all*
   cyclones (via `expand()` over the cyclone list) into
   `outputs/extreme_value_stats/...`. Uses `script:`.

**Resulting tree:**

```
<workflow-root>/
  CLAUDE.md
  Snakefile
  config.yaml
  pixi.toml / pixi.lock
  rules/
    extract_bathymetry_chunk.smk   # only if bathymetry isn't already per-cyclone
    prepare_model_input.smk
    run_model.smk
    summarize_run_log.smk
    per_cyclone_stats.smk
    extreme_value_stats.smk
  scripts/
    per_cyclone_stats.py
    extreme_value_stats.py
    summarize_run_log.py
  data/
    cyclones/<cyclone_id>.*
    bathymetry/...                   # global file, or already-chunked per cyclone — either way, just data
  templates/
    model/                             # never run in place, only ever copied from
  scratch/
    <cyclone>/bathymetry_chunk.*         # only if the chunking rule ran
    <cyclone>/run/                         # staged template copy + model's own output + its raw log
  outputs/
    <cyclone>/stats.csv
    <cyclone>/figures/*.png
    extreme_value_stats/...
  logs/
    <cyclone>/run_model.log               # Snakemake's own orchestration log
    <cyclone>/summary.log                   # distilled from the raw log in scratch/
  .gitignore                                # scratch/ always ignored
```

The cyclone-specific names above (`cyclones/`, `bathymetry/`, `model/`) are
illustrative, not prescriptive — the categories (`data/`, `templates/`,
`scratch/`, `outputs/`, `logs/`) are the generalizable part.

## Proposed general structure

```
<workflow-root>/
  CLAUDE.md              # self-contained docs: structure, how to run, generated once
  Snakefile                # entry point; includes rules/*.smk
  config.yaml               # parameters the rules read via `config[...]`
  pixi.toml / pixi.lock       # environment (snakemake itself + any task deps), consistent
                                # with this repo's own pixi-based convention (see AGENTS.md)
  rules/
    <step_name>.smk            # one logical step per file, included from Snakefile
  scripts/
    <step_name>.py               # the actual work a rule's `script:` directive runs
                                     # (only for rules that run custom code — see shell: vs script: below)
  data/                          # raw/external inputs — case-specific or shared, chunked or not; see "Structural categories"
  templates/                       # generic skeletons, always copied-and-modified per case, never run/read in place
  scratch/                           # disposable per-case working/run output — regenerable, safe to delete after success
  outputs/                             # lean, valuable, kept-forever results
  logs/                                  # Snakemake's own per-rule logs + distilled summaries of heavy logs living in scratch/
  .gitignore                              # at minimum, scratch/
```

**Discovery marker**, same mechanism as `local-library`'s
`local-library-root: v1`: root `CLAUDE.md` starts with
`<!-- snakemake-workflow-root: v1 -->`, greppable via:

```bash
rg -l 'snakemake-workflow-root: v1' --glob CLAUDE.md
```

## Scripted helper(s)

Mirroring `local-library`'s `init-library.py` (mechanical, idempotent,
never overwrites existing files):

- **`init-workflow.py [path/to/workflow-root]`** — scaffolds the structure
  above: `CLAUDE.md` (with the marker line + generic structural docs, same
  "fill in the purpose at the top" pattern as `local-library`), an empty
  `Snakefile` that just `include:`s everything under `rules/`, a starter
  `config.yaml`, `pixi.toml` with `snakemake` as a dependency, the
  `rules/`/`scripts/`/`data/`/`templates/`/`scratch/`/`outputs/`/`logs/`
  directories, and `.gitignore` (at minimum `scratch/`, `.snakemake/`).
  Defaults to `./workflow` if no path given, matching `local-library`'s
  `./local_library` default convention. Safe to re-run.
- Not every workflow needs all of `templates/`/`scratch/`/`outputs/` —
  e.g. a workflow with no per-case template-copying has no real use for
  `templates/` or `scratch/`. `init-workflow.py` still creates the full set
  for consistency; an agent extending the workflow later just doesn't
  populate the ones that don't apply, rather than the script trying to
  guess upfront which apply.

No further scripted helpers are planned yet (e.g. a `local-library`-style
status/drift checker is a plausible future addition — see Open Questions —
but isn't part of the initial skill).

## Agent-judgment workflows (instructions, not scripts)

**Scaffolding a new workflow:**
1. Run `init-workflow.py` to get the skeleton in place.
2. Fill in `CLAUDE.md`'s purpose line and `config.yaml` with whatever
   parameters the user's task actually needs — don't leave placeholder
   values that look real.
3. Translate the user's task into one or more rules (see below) rather than
   one monolithic rule, unless the task genuinely is a single step.

**Adding a rule:**
1. Understand the step well enough to know its real inputs, outputs, and
   parameters — not just "runs a script."
2. One rule per logical step, in its own `rules/<step_name>.smk`, wired in
   via the `Snakefile`'s blanket `include:`.
3. **`shell:` vs. `script:`** — use `shell:` when the step is invoking an
   external program (a model binary, a CLI tool); use `script:` with a
   paired `scripts/<step_name>.py` when the step is custom Python. Don't
   force every rule through a wrapper `.py` file just for consistency —
   `run_model` in the worked example above is a `shell:` rule precisely
   because there's no Python to wrap.
4. **Template-copy pattern**: if a step needs an isolated working copy of
   something reusable (a model template, a config skeleton) rather than
   being safely re-runnable in place, split "stage a copy and adjust it for
   this case" into its own rule, separate from "do the actual work in that
   copy." This keeps the "do the work" rule reusable even for cases that
   don't need a template at all, and avoids re-staging on a rerun that only
   needs the expensive step repeated.
5. **Disposable vs. kept outputs**: before wiring up a rule's output path,
   ask whether it's something to keep (`outputs/`) or working material
   that's fully regenerable and only useful while debugging
   (`scratch/`) — don't default everything into one or the other.
6. Always declare `log:` for anything that can fail non-obviously, and
   `threads:`/resource directives when the step is genuinely parallelizable
   or memory-heavy — don't add them reflexively for trivial steps.
7. Wire `config.yaml` entries for anything that should be user-tunable
   without editing the rule itself.

**Running — dry-run discipline (same spirit as `pdf-to-markdown`'s
estimate-before-converting pattern):**
1. Before any real run, `snakemake -n -p [target]` (dry run, print shell
   commands) to confirm the DAG is what's expected — which rules fire, in
   what order, for which files.
2. For a non-trivial run (long-running steps, or touches/regenerates a lot
   of existing `scratch/`/`outputs/`), surface the dry-run's plan and ask
   for confirmation before running for real — don't silently kick off a
   long pipeline the user didn't explicitly sign off on.
3. Run for real with `snakemake --cores N [target]` once confirmed.
4. `snakemake --dag | dot -Tsvg > dag.svg` (or equivalent) is worth offering
   when a user wants to *see* the pipeline structure, not just run it.

**Cleaning up `scratch/`:** once a case's `outputs/` and `logs/` look
correct, `scratch/<case>/` can be deleted without losing anything
structurally useful — it's regenerable from `data/` + `templates/` by
rerunning the rules that produced it. This is a manual, explicit decision
the user makes per case (or wholesale), not something a rule does
automatically. Implemented as `scripts/clean-workflow.py` (default:
`scratch/` only; `--all`: also `outputs/`+`logs/`+`.snakemake/` — see
`SKILL.md`'s "Cleaning up" for the full split and the confirm-before-`--all`
guidance).

**Important caveat, found by actually testing this**: "regenerable" means
*can be forced to regenerate*, not that a plain rerun will do it
automatically. If a downstream kept output (e.g. in `outputs/`) still
exists, `snakemake [target]` after cleaning `scratch/` reports "Nothing to
be done" — Snakemake doesn't walk back to verify every upstream
intermediate is still physically present once the target looks up to date.
Regenerating a cleaned `scratch/` requires `snakemake --forcerun <rule>
[target]` naming the rule(s) that populate it, not just the same command
again.

**Environment management:** one project-wide `pixi.toml`/`pixi.lock` for
the whole workflow (Snakemake itself, plus whatever each rule's script
needs), consistent with this repo's existing pixi-first convention — not
per-rule conda environments, unless a specific rule has a genuinely
conflicting dependency that forces it.

## Open questions

- **Wrapping existing ad-hoc scripts** (user already has loose
  scripts/notebooks, agent turns them into rules) and **extending an
  existing workflow** (adding a rule to one that already exists, from this
  skill or not) — both deferred past the initial scaffold-from-scratch use
  case; revisit once that's working.
- **Status/drift checking**, analogous to `local-library`'s
  `show-library.py` — resolved: implemented as a bespoke script,
  `scripts/summarize-workflow.py` (pure directory/text introspection, no
  `snakemake --summary`/`--list-target-rules` invocation needed). Reports
  the workflow's purpose, declared-vs-included rule drift, and — only for
  folders that actually use per-case subfolders — which cases ran
  (`scratch/`) but produced no kept output (`outputs/`). Tested against
  both example workflows; the per-case check had to be taught to skip flat
  (aggregated) folders specifically, or it false-flagged every
  successfully-completed case in a workflow whose final rule collects
  everything into one combined file rather than per-case outputs.
- **Per-rule environments**: stick with single project-wide `pixi.toml`
  always, or document an escape hatch for genuinely conflicting
  dependencies (conda env per rule via Snakemake's own `conda:` directive)?
  Leaning toward "document the escape hatch, default to one pixi env," not
  decided.
- Future relationship to the `reporting` (Quarto) skill once that's
  designed — e.g. whether a workflow's `outputs/` is a natural input to a
  Quarto report — intentionally out of scope for *this* skill's design, but
  worth a cross-reference once both exist.
