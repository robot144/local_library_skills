---
name: agent-runner
description: Launch a coding agent session (Claude Code only, v1) from a script, with automatic vendor resolution and settings control - usable standalone or as a `workflow` Snakemake pipeline step. Use when a task needs an agent's reasoning/tool access (web lookup, interpretation, judgment) as one step in an otherwise scriptable pipeline, or to run an agent over many inputs as a batch. Not needed for deterministic computation - that's what `workflow` already handles without this.
---

# Agent Runner

Launches a coding agent session from a script, through a single
`launch_agent` entry point — usable directly as a Python call, or as the
`shell:`/`script:` step of a `workflow` Snakemake rule, so an agent run
can be one step in a larger, possibly batched pipeline, not only something
a human kicks off interactively.

**First version, deliberately scoped small.** Only Claude Code is
implemented as a vendor — the full design (worked examples, open
tensions, what's deferred on purpose) lives in
[`agent-runner_design.md`](../../agent-runner_design.md); this `SKILL.md`
covers what's actually built. Read the design doc for the reasoning
behind the decisions below, not just the decisions themselves.

**Independent of `workflow`/`reporting`/`local-library`.** Works
standalone; composes with `workflow` when an agent step needs to sit
inside a pipeline (see the design doc's "Katrina" and eval-harness worked
examples).

## Core function: `launch_agent`

```python
result = launch_agent(
    "Summarize what this directory contains.",
    vendor=None,           # None = auto-resolve, see "Vendor resolution" below
    cwd="./scratch/case1", # working directory for the agent run
    settings={"model": "claude-sonnet-5", "permission_mode": "acceptEdits"},
    timeout=300,
)
# result.exit_code, result.structured_output, result.transcript_path
```

Returns an `AgentRunResult` (vendor, exit code, cwd, transcript path,
parsed structured output if the agent's response was valid JSON). Raises
`VendorResolutionError` only on setup failure (no resolvable or
implemented vendor) — never just because the agent's own task failed;
that's part of the result, not an exception.

**A "judge" run is just a second `launch_agent` call** with `cwd` pointed
at the subject run's output directory — see the design doc's eval-harness
worked example. No separate judge function exists or is needed.

## Vendor resolution

Fallback chain, always in this order, never a silent guess:

1. **Explicit** — `vendor=...` / `--vendor` CLI flag.
2. **`config.yaml`** — the `agent_vendor` key, read from `./config.yaml`
   or wherever `--config`/`config_path` points.
3. **Environment auto-detect** — checks for `CLAUDECODE=1` (confirmed by
   testing: `env | grep -i claude` inside an actual Claude Code session).
   Only this one marker exists in v1; add more as other vendors are
   actually targeted.
4. **Clear, actionable error** — never a PATH-search guess, never an
   arbitrary default.

**Env-var detection is for scaffold time, not every run.** A workflow
should be rerunnable later with no agent attached at all (see the design
doc's "Resolved: starting a workflow without a live agent session") — so
the normal path is: detect once when a rule is first set up, persist the
result into `config.yaml`, and every later run just reads that file.

```bash
python3 scripts/run-agent.py --write-default-vendor config.yaml
```

Run this once per workflow when scaffolding a rule that needs
`agent-runner` — writes `agent_vendor: claude-code` into `config.yaml` if
the key isn't already set there (never overwrites an existing value).
Safe to re-run; a no-op once the key exists.

```bash
python3 scripts/run-agent.py --detect-vendor
```

Prints the auto-detected vendor (or errors) without launching anything —
useful for checking what a given shell would default to.

## CLI usage (for a `workflow` rule's `shell:` step)

```bash
python3 scripts/run-agent.py "<prompt>" --cwd ./scratch/case1/run --output result.json
python3 scripts/run-agent.py --prompt-file prompt.txt --vendor claude-code --model claude-sonnet-5
```

`--output result.json` writes the full `AgentRunResult` as JSON — the
natural thing for a downstream rule to consume. The transcript (`claude`'s
own JSON output) is always saved to `<cwd>/agent_transcript.json`
regardless of `--output`.

**Model selection has two paths — know both, since they can silently
conflict.** `--model`/`settings["model"]` is the explicit, documented one.
But `launch_agent` doesn't override the child process's environment, so
`claude -p` also inherits (and respects) `ANTHROPIC_MODEL` from whatever
shell invoked it — confirmed by testing: setting `ANTHROPIC_MODEL=
claude-fable-5` with no `--model` flag actually changed which model the
nested session used, even though `ANTHROPIC_MODEL` isn't documented in
`claude --help`. If you need a specific model, pass `--model` explicitly
rather than relying on whatever `ANTHROPIC_MODEL` happens to be set to in
the calling shell — it's easy to get an unintended model this way if an
outer session's own env leaks through.

**A third option: `settings["size"]`/`--size` (`small`/`medium`/`large`)**
— a vendor-agnostic convenience alias, translated per-vendor
(`small`→`haiku`, `medium`→`sonnet`, `large`→`opus` for Claude Code).
`--model`/`settings["model"]` wins if both are given. This is a
deliberately "good enough, not perfect" mapping, not validated against
any other vendor (there isn't a second adapter yet) and not covering
every model this vendor has — `fable` doesn't fit a size scheme at all
(it's a different axis, not "bigger than large"), so it stays reachable
only via `--model` directly. The point is a reasonable default for
callers that aren't optimizing for a specific agent — when a workflow is
small, that optimization doesn't pay off anyway. An unrecognized size
raises a clear `ValueError` (`--list-models`/`unknown size '...'
(recognized: small, medium, large)`), not a silent fallback.

## Discovering available models

```bash
python3 scripts/run-agent.py --list-models
```

Free — confirmed by testing (`total_cost_usd: 0`, no real API call).
Prints the current default and every recognized model name/alias (e.g.
`sonnet, opus, haiku, fable, ...`) via Claude Code's own `/model` command.
This tells you which **names** are recognized, not which ones currently
have remaining usage credits — those are two different things, confirmed
by testing: `claude-fable-5` is a recognized name that still failed from
credit exhaustion in practice. There's no free way to check *that* in
advance; it's a live, per-model, costly probe — see the design doc's
"Deferred past v1."

**If a requested `--model` doesn't exist or isn't accessible, `launch_agent`
surfaces the available models automatically** — on `AgentRunResult.
available_models` (`{"current": ..., "available": [...]}`), or as a
"Hint:" line in the CLI output. Confirmed by testing: `claude -p --model
<bad-name> ...` exits with code **0** even though it failed (`is_error:
true` in its JSON) — `launch_agent`/`main()` check `is_error`, not just
the exit code, specifically because of this; don't assume exit code 0
means success when inspecting a result yourself.

## Adding a rule that uses this

Same pattern as any `workflow` rule (see that skill's "Adding a rule"):
one rule per step, `shell:` invoking `run-agent.py` directly (it's already
a script, no wrapper needed). Treat the agent step's structured output as
*frozen* once produced — don't let Snakemake casually rerun it the way it
would a deterministic computation; see the design doc's non-determinism
discussion for why.

## What's deliberately not here yet

- **Only Claude Code.** No Codex/Copilot/other adapters — add them as
  they're actually needed, following `ClaudeCodeAdapter`'s shape.
- **No capability discovery beyond model names.** `--list-models` tells
  you which model names are recognized (free), not whether a given one
  has remaining usage credits, or whether a vendor has web access, etc. —
  just launches the resolved vendor and sees if the step works for
  anything beyond model-name validity; results vary by agent, accepted as
  a v1 limitation.
- **No safety/sandboxing beyond what `settings` (e.g. `permission_mode`,
  `allowed_tools`) already lets you restrict.** An agent step can take
  real actions; nothing here enforces extra guardrails on top of what you
  configure explicitly.
- **No dedicated credential handling.** Relies entirely on whatever auth
  is already configured in the ambient environment the script runs in.

See `agent-runner_design.md`'s "Known tensions" and "Not yet decided" for
the full list and the reasoning behind each.
