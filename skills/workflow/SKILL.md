---
name: workflow
description: Scaffold and extend reproducible research workflows using Snakemake — domain-agnostic (simulations, data processing, batch per-case runs, anything with repeatable steps and real inputs/outputs). Use when the user wants to "set up a reproducible workflow for X," "turn these scripts into a pipeline," "run this model/step for every [case/file/event]," mentions Snakemake directly, or describes a multi-step process with inputs feeding outputs that should be re-runnable rather than run by hand each time. Not needed for a true one-off script with no reruns and no real dependency structure.
---

# Workflow (Snakemake)

Scaffolds and extends reproducible research workflows built on
[Snakemake](https://snakemake.github.io/) — domain-agnostic: this skill
teaches how to structure and extend a Snakemake-based workflow, not any
particular kind of research task.

**This skill is mostly instructions, not automation**, same split as
`local-library`: the mechanical pieces (scaffolding a new workflow,
emptying its disposable folders, summarizing its current state) have
small helper scripts; designing rules, deciding what's disposable vs.
worth keeping, and wiring dependencies are judgment calls, documented as
instructions below.

**Independent of `local-library`.** A project can have both, but neither
assumes the other exists.

## Structure

```
<workflow-root>/
  CLAUDE.md              # self-contained docs: structure, how to run - generated once
  Snakefile                # entry point: configfile + one include: line per rules/*.smk file
  config.yaml               # parameters rules read via config["..."]
  pixi.toml / pixi.lock       # environment: snakemake + whatever each rule's script needs
  rules/
    <step_name>.smk            # one logical step per file, wired in via the Snakefile's include: lines
  scripts/
    <step_name>.py               # the actual work a rule's `script:` directive runs
                                     # (only for rules running custom Python - see "shell: vs script:" below)
  data/                          # raw/external input - case-specific or shared, pre-chunked or not; doesn't matter here
  templates/                       # generic skeletons, always copied-and-modified per case, never read/run in place
  scratch/                           # disposable per-case working/run output - regenerable, safe to delete once outputs/+logs/ look right
  outputs/                             # lean, valuable, kept-forever results
  logs/                                  # Snakemake's own per-rule logs + distilled summaries of any heavy logs living in scratch/
  .gitignore                              # at minimum, scratch/ and .snakemake/
```

`<workflow-root>` has no fixed name, same stance as `local-library`'s root
— whatever directory the user is organizing the workflow in.

**Not every workflow needs every folder.** `templates/` and `scratch/`
only earn their place when some step needs an isolated per-case working
copy of something reusable; a workflow that's just "read `data/`, write
`outputs/`" doesn't need either. `init-workflow.py` (below) still creates
the full set for consistency — just don't force content into a folder that
doesn't apply to the task at hand.

## Structural categories: what goes where

Four roles — named here for what they *are*, not fixed folder names (if
everything under what would be `templates/` is genuinely just templates,
call it that; there's no requirement to nest it under some more generic
label):

- **`data/`** — any raw/external input the user provided, never produced
  by a rule. Whether it's shared across every case or already split
  per case, and whether it needs a derivation step before use or is ready
  to use directly, is **not** a property of the data itself — it's an
  accident of how it arrived, and it only changes which rules exist in the
  DAG, not which folder it lives in. Don't split `data/` into "shared" vs.
  "per-case" subfolders on the assumption that distinction is stable; it
  usually isn't (e.g. a shared reference dataset might arrive as one global
  file needing a per-case extraction rule, or already pre-chunked per case
  with no extraction rule needed at all — same folder either way).
- **`templates/`** — the one category that's genuinely structurally
  different: a template is always copied wholesale and then modified for a
  specific case, never read-and-derived-from in place. That different
  relationship to the workflow is why it's worth its own category even
  though it's also "just input the user provided."
- **`scratch/`** — disposable, per-case working/run output. Fully
  regenerable from `data/` + `templates/` by rerunning the rules that
  produced it. Holds anything heavy not worth keeping once you trust the
  result: staged template copies, a model's own run output, and (per the
  log-handling pattern below) a model's own raw, huge, internal log files.
- **`outputs/`** and **`logs/`** — the same pattern applied twice: lean,
  valuable, *kept-forever* distillations of something heavy and disposable
  living in `scratch/`.
  - `outputs/` — the actual results worth keeping (stats, figures,
    aggregates).
  - `logs/` — two things: Snakemake's own per-rule orchestration log (via
    the rule's `log:` directive — always small, catches "did the
    shell/script invocation itself fail") **and**, where relevant, a small
    summary distilled from a model's huge internal log that otherwise
    lives in `scratch/<case>/...` alongside the rest of that run. What
    counts as a "main item" worth keeping in the summary (errors, warnings,
    convergence info, timing) is task-specific judgment — document the
    pattern for the specific workflow, don't assume one universal format.

## Setting up a new workflow

```bash
python3 scripts/init-workflow.py [path/to/workflow-root]
```

Defaults to `./workflow` if no path is given. Creates `CLAUDE.md`
(self-contained structural docs — fill in the workflow's purpose at the
top, the rest is generic), a starter `Snakefile`, `config.yaml`,
`pixi.toml` (with Snakemake as a dependency), the full set of folders
above, and a `.gitignore` covering `scratch/` and Snakemake's own
`.snakemake/` cache dir. Safe to re-run — never overwrites a file that
already exists. If the user already has a workflow laid out differently,
don't force it into this shape; adapt to what's there instead.

## Finding existing workflows

Every workflow root's `CLAUDE.md` starts with a dedicated marker line,
`<!-- snakemake-workflow-root: v1 -->` (same mechanism `local-library` uses
for its own roots). Find every instance under a directory tree with:

```bash
rg -l 'snakemake-workflow-root: v1' --glob CLAUDE.md
```

Use this before assuming no workflow exists yet, or when the user asks "is
there already a workflow for X" without naming a path.

## Summarizing a workflow

```bash
python3 scripts/summarize-workflow.py [path/to/workflow-root]
```

Defaults to `./workflow` if no path is given. Prints the workflow's
purpose (from `CLAUDE.md`'s title), every rule declared under `rules/`
cross-checked against the Snakefile's `include:` lines (flags a rule file
that's never included, or an `include:` pointing at a file that doesn't
exist), and — when `scratch/`, `outputs/`, or `logs/` use per-case
subfolders — a per-case presence check across them (flags a case that ran
but never produced a kept output). Pure directory/text introspection, no
Snakemake invocation needed, so it works even before `pixi install`. Use
this when the user asks what's in a workflow, wants a status check, or you
suspect a run failed partway through.

**Only cross-checks folders that actually use per-case subfolders.** A
folder that aggregates every case into one flat file (e.g. a `collect_*`
rule's single combined output) isn't missing anything just because it has
no subfolder named after a given case — the summary says so explicitly
(`not checked per-case - flat/aggregated: ...`) rather than printing a
false "missing output" flag. Confirmed by testing: a workflow with a flat
`outputs/` initially flagged every one of its successful cases as "ran but
no kept output yet," which was wrong — fixed by excluding flat folders from
the per-case check entirely, not just from the display.

For Snakemake's own target-specific generated-file status, explicitly opt
into a second, environment-dependent section:

```bash
python3 scripts/summarize-workflow.py [path/to/workflow-root] \
  --snakemake-summary <target>
```

This runs `pixi run snakemake --summary <target>` in the workflow root and
reports each output's producing rule, log, status, and update plan. It is
deliberately opt-in: unlike the default summary, it requires a working Pixi
environment and asks Snakemake to resolve the selected target.

## Adding a rule

1. **Understand the step first** — its real inputs, outputs, and
   parameters, not just "runs a script."
2. **One rule per logical step**, in its own `rules/<step_name>.smk`, added
   to the `Snakefile` with its own `include: "rules/<step_name>.smk"` line.
3. **`shell:` vs. `script:`** — use `shell:` when the step invokes an
   external program (a model binary, a CLI tool); use `script:` with a
   paired `scripts/<step_name>.py` when the step is custom Python. Don't
   force every rule through a wrapper `.py` just for consistency — a rule
   that only runs an external binary has no Python to wrap.
4. **Template-copy pattern** — if a step needs an isolated working copy of
   something reusable (a model template, a config skeleton) rather than
   being safely re-runnable in place, split "stage a copy and adjust it for
   this case" into its own rule, separate from "do the actual work in that
   copy." This keeps the "do the work" rule reusable even for cases that
   don't need a template at all, and avoids re-staging on a rerun that only
   needs the expensive step repeated.
5. **Disposable vs. kept outputs** — before wiring up a rule's output path,
   decide whether it's something to keep (`outputs/`) or working material
   that's fully regenerable and only useful for debugging (`scratch/`).
   Don't default everything into one or the other.
6. Always declare `log:` for anything that can fail non-obviously, and
   `threads:`/resource directives when the step is genuinely parallelizable
   or memory-heavy — don't add them reflexively for trivial steps.
7. Wire a `config.yaml` entry for anything that should be user-tunable
   without editing the rule itself.

## Running a workflow — dry-run discipline

Same spirit as `pdf-to-markdown`'s estimate-before-converting pattern: know
what's about to happen before committing to it, especially for anything
long-running.

1. **Dry run first**: `snakemake -n -p [target]` — confirms the DAG is what
   you expect (which rules fire, in what order, for which files) without
   running anything.
2. **Confirm before a non-trivial real run** — long-running steps, or
   anything that touches/regenerates a lot of existing `scratch/`/
   `outputs/` — surface the dry run's plan and ask before running for
   real. Don't silently kick off a long pipeline the user didn't explicitly
   sign off on.
3. **Run for real**: `snakemake --cores N [target]`, once confirmed.
4. **Visualizing the DAG** is worth offering when the user wants to *see*
   the pipeline structure, not just run it — see "Visualizing a DAG" below.

## Visualizing a DAG

Use an explicit target so the graph represents the actual requested work:

```bash
pixi run snakemake --dag <target> > dag.dot          # expanded job DAG
pixi run snakemake --rulegraph <target> > rules.dot  # one node per rule
pixi run snakemake --filegraph <target> > files.dot  # files and rules
```

DOT is Snakemake's exact graph representation. If Graphviz is available,
render it to an SVG with `dot -Tsvg dag.dot > dag.svg`. Do not offer an
ASCII terminal renderer unless the workflow explicitly declares and installs
one as a reproducible dependency.

For a Markdown document that renders in GitHub, VS Code, Quarto, or another
Mermaid-capable renderer, use the helper:

```bash
python3 scripts/render-workflow-dag.py [path/to/workflow-root] \
  --target <target> --output DAG.md
```

It invokes `pixi run snakemake --dag <target>` and writes an expanded
Mermaid flowchart. Use `--format dot` when a downstream Graphviz or DOT tool
needs the native graph instead.

## Cleaning up

```bash
python3 scripts/clean-workflow.py [path/to/workflow-root]          # scratch/ only - always safe
python3 scripts/clean-workflow.py [path/to/workflow-root] --all      # scratch/ + outputs/ + logs/ + .snakemake/
python3 scripts/clean-workflow.py [path/to/workflow-root] --all --dry-run   # report what would be emptied, change nothing
```

Defaults to `./workflow` if no path is given. Each targeted directory is
emptied and left in place (so the standing folder structure survives) —
`scratch/`, `outputs/`, and `logs/` are recreated empty with a fresh
`.gitkeep`; Snakemake's own `.snakemake/` cache is just removed outright.

**Default mode (`scratch/` only) is always safe to run without asking** —
it's regenerable from `data/` + `templates/` by rerunning the rules that
produced it, so emptying it loses nothing structurally useful.

**"Regenerable" needs a forceful rerun, not just the same command again.**
Confirmed by testing: if a downstream kept output (e.g. something in
`outputs/`) still exists, a plain `snakemake [target]` after cleaning
`scratch/` reports "Nothing to be done" — Snakemake only rebuilds what it
believes is stale, and doesn't walk back to verify every upstream
intermediate file is still physically present once the target itself looks
up to date. To actually regenerate a cleaned `scratch/`, force the rule(s)
that populate it: `snakemake --forcerun <rule_that_wrote_scratch> [target]`
(add every such rule name needed). Don't tell a user "just rerun it" after
cleaning `scratch/` without the `--forcerun` — plain reruns silently do
nothing in that case.

**`--all` is a different kind of decision, not a bigger version of the
same one.** It also empties `outputs/` and `logs/` — the categories this
skill treats as kept-forever specifically because they might represent
expensive, hard-to-reproduce work. Dry-run it first, and don't run it for
real without the user's go-ahead, the same way you wouldn't kick off a
long `run_model` without confirming first (see "Running a workflow"
above) — the risk here is symmetric: skipping confirmation before an
expensive run and skipping confirmation before deleting that run's output
are the same mistake in opposite directions.

## Environment management

One project-wide `pixi.toml`/`pixi.lock` for the whole workflow (Snakemake
itself, plus whatever each rule's script needs), consistent with this
repo's pixi-first convention — not per-rule conda environments, unless a
specific rule has a genuinely conflicting dependency that forces it (in
that case, Snakemake's own `conda:` directive on that one rule is the
escape hatch, not a restructuring of the whole environment).

**Keep this manifest self-contained.** `pixi run`/`pixi install` always
use the *nearest* `pixi.toml` walking up from the current directory, with
no merging from a parent manifest — so a workflow nested inside a project
that has its own `pixi.toml` (common: the workflow is one piece of a larger
repo) must declare everything it needs itself, including `python`, rather
than relying on a dependency some ancestor manifest happens to provide.
When adding a dependency for a new rule's script, add it to *this*
`pixi.toml`, and don't drop `python` on the assumption `snakemake-minimal`
pulling it in transitively is good enough — make it explicit.
