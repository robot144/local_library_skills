#!/usr/bin/env python3
"""Scaffold a new Snakemake-based workflow root: CLAUDE.md (self-contained
structural docs), a starter Snakefile, config.yaml, pixi.toml, the
data/templates/scratch/outputs/logs/rules/scripts folders, and a
.gitignore covering scratch/ and .snakemake/. Never overwrites a file that
already exists.

Usage: python3 init-workflow.py [path/to/workflow-root]
Defaults to ./workflow if no path is given.
"""
import sys
from pathlib import Path

DEFAULT_ROOT = "workflow"

# Folders created every time, even if a given workflow won't end up using
# all of them (e.g. one with no per-case template-copying has no real use
# for templates/ or scratch/) - consistency over guessing what applies.
FOLDERS = ["rules", "scripts", "data", "templates", "scratch", "outputs", "logs"]

# scratch/ is gitignored wholesale, so it doesn't need a .gitkeep to
# survive being committed empty - git already ignores empty dirs regardless.
GITKEEP_FOLDERS = ["rules", "scripts", "data", "templates", "outputs", "logs"]

CLAUDE_MD_TEMPLATE = """\
<!-- snakemake-workflow-root: v1 -->
# <Describe what this workflow does here>

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
- `scratch/` - disposable per-case working/run output. Regenerable
  from `data/` + `templates/` by rerunning the rules that produced it -
  safe to delete once `outputs/` and `logs/` for that case look right.
- `outputs/` - the lean, valuable, kept-forever results.
- `logs/` - Snakemake's own per-rule logs (via each rule's `log:`
  directive) plus, where relevant, small summaries distilled from any
  heavy logs that live in `scratch/` alongside a case's run output.

Not every workflow uses every folder - e.g. one with no per-case
template-copying has no real need for `templates/` or `scratch/`.

`scripts/clean-workflow.py` empties `scratch/` (always safe) or, with
`--all`, also `outputs/`+`logs/`+`.snakemake/` (only once you're sure
nothing there is still needed).

## Running

```bash
snakemake -n -p [target]      # dry run first - confirm the DAG before running anything
snakemake --cores N [target]    # run for real, once the dry run looks right
```

**After cleaning `scratch/`, a plain rerun of the same target is not
enough** if a downstream kept output still exists - Snakemake sees the
target is already there and reports "Nothing to be done" without checking
that its upstream intermediates were deleted. Force the rule(s) that
populate `scratch/` instead: `snakemake --forcerun <rule> [target]`.

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
"""

SNAKEFILE_TEMPLATE = """\
configfile: "config.yaml"


# Add one include: line per rule file as you create it under rules/.
# include: "rules/example_step.smk"
"""

CONFIG_YAML_TEMPLATE = """\
# Parameters your rules read via config["..."]. Fill in as rules need them.
# (Must stay a mapping - Snakemake's configfile: rejects an empty/null file.)
{}
"""

PIXI_TOML_TEMPLATE = """\
[workspace]
name = "workflow"
version = "0.1.0"
channels = ["conda-forge", "bioconda"]
platforms = ["linux-64"]

[dependencies]
# python is listed explicitly (not left to snakemake-minimal's transitive
# dependency) so this manifest is self-contained: `pixi run`/`pixi install`
# always use the *nearest* pixi.toml walking up from cwd, with no merging
# from a parent manifest, so a workflow nested inside a project that has
# its own pixi.toml (e.g. this skill's own repo) must not depend on
# anything from that outer manifest to function.
python = ">=3.10,<3.14"
snakemake-minimal = ">=8,<9"
# Swap to `snakemake = ">=8,<9"` instead if you need the extra reporting/
# plotting dependencies snakemake-minimal leaves out.
"""

GITIGNORE_TEMPLATE = """\
scratch/
.snakemake/
.pixi/
"""


def write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        print(f"==> {path.name} already exists, leaving it untouched: {path}")
    else:
        path.write_text(content, encoding="utf-8")
        print(f"==> Created {path}")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()

    for name in FOLDERS:
        (root / name).mkdir(exist_ok=True)
    for name in GITKEEP_FOLDERS:
        keep = root / name / ".gitkeep"
        if not any((root / name).iterdir()):
            keep.touch()

    write_if_missing(root / "CLAUDE.md", CLAUDE_MD_TEMPLATE)
    write_if_missing(root / "Snakefile", SNAKEFILE_TEMPLATE)
    write_if_missing(root / "config.yaml", CONFIG_YAML_TEMPLATE)
    write_if_missing(root / "pixi.toml", PIXI_TOML_TEMPLATE)
    write_if_missing(root / ".gitignore", GITIGNORE_TEMPLATE)

    print(f"\nDone. Workflow root: {root}")
    print(f"Next steps:\n  cd {root} && pixi install && pixi run snakemake -n -p")
    return 0


if __name__ == "__main__":
    sys.exit(main())
