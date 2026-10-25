<!-- snakemake-workflow-root: v1 -->
# Example multi-run workflow: expression evaluator

Simplified stand-in for a multi-run model: `data/expressions.txt` holds one
math expression per line. `split_expressions` stages each one into its own
`scratch/<case>/` folder (the "prepare" step); `compute_expression`
evaluates it there (the "run" step, generic - doesn't know or care where
its input came from); `collect_results` gathers every case's answer into
one `outputs/results.txt`.

This is a Snakemake-based reproducible workflow. Start at the Snakefile for
the current set of steps; config.yaml holds the parameters they read.

## Structure

- `rules/<step_name>.smk` - one logical step per file, wired into the
  Snakefile via its own `include:` line.
- `scripts/<step_name>.py` - the actual work for any rule using a `script:`
  directive (rules invoking an external program instead use `shell:` and
  have no paired script).
- `data/` - raw/external input, never produced by a rule. Shared vs.
  per-case, and pre-processed vs. not, doesn't change which folder it's
  in - only which rules exist to process it.
- `templates/` - generic skeletons, always copied wholesale and then
  modified for a specific case, never read or run in place.
- `scratch/` - disposable per-case working/run output. Fully regenerable
  from `data/` + `templates/` by rerunning the rules that produced it -
  safe to delete once `outputs/` and `logs/` for that case look right.
- `outputs/` - the lean, valuable, kept-forever results.
- `logs/` - Snakemake's own per-rule logs (via each rule's `log:`
  directive) plus, where relevant, small summaries distilled from any
  heavy logs that live in `scratch/` alongside a case's run output.

Not every workflow uses every folder - e.g. one with no per-case
template-copying has no real need for `templates/` or `scratch/`.

## Running

```bash
snakemake -n -p [target]      # dry run first - confirm the DAG before running anything
snakemake --cores N [target]    # run for real, once the dry run looks right
```

Ask before a real run that's long-running or touches a lot of existing
`scratch/`/`outputs/` - don't silently kick off a long pipeline unprompted.

## Adding a rule

One rule per logical step, in its own `rules/<step_name>.smk`, added to the
Snakefile with its own `include:` line. `shell:` for external programs,
`script:` + a paired `scripts/<step_name>.py` for custom Python. If a step
needs an isolated working copy of something in `templates/`, stage that
copy in its own rule, separate from the rule that does the actual work -
keeps the "do the work" rule reusable for cases that don't need a template
at all.
