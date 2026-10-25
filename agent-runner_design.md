# Design: `agent-runner` skill (working name)

Status: implemented (first version, Claude Code only). See
[`skills/agent-runner/SKILL.md`](skills/agent-runner/SKILL.md) for the
skill itself — this file remains the design record (worked examples,
rationale, open questions) behind those decisions. The skill's actual
name is still just a working name, not finalized.

## Goals

1. **Start a new coding agent session through a Python layer.**
   Programmatically launch an agent (Claude Code, Codex CLI, Copilot CLI,
   etc.) rather than requiring a human to invoke that CLI by hand.
2. **The Python layer controls agent settings and is vendor-agnostic.**
   One interface for configuring and launching a session — model choice,
   permissions, whatever else varies per agent — so a caller doesn't need
   agent-specific logic just to say "run this task with an agent."
3. **The same scripts should double as workflow steps.** Usable both as a
   standalone way to launch an agent, and as a rule/step inside a
   `workflow`-skill Snakemake pipeline (a `shell:`/`script:` target) — so
   an agent run can be one step in a larger, automated, possibly batched
   pipeline, not only something a human kicks off interactively.

## Why this might fit well with what's already here

`workflow`'s rules already expect exactly this script shape — args in,
runs, produces output, exits — so a script that launches an agent isn't a
stretch to plug in as a rule's `shell:`/`script:` step. Combined with
`workflow`'s per-case wildcarding (see `workflow_design.md`'s cyclone
example), this could enable "run an agent over N inputs, collect the
results" as a batch pipeline, the same shape as any other multi-run
workflow in that skill — just with an agent session as the thing being
run per case instead of a numerical model.

## Worked example: "Katrina" → a tide-gauge report

A concrete use case, stress-tested against the goals above before
generalizing them (same role the cyclone example played in
`workflow_design.md`): the user names a storm — "Katrina" — and that
alone kicks off an entire pipeline: look up the storm's characteristics
on the internet, turn those into a region and time-span, pull tide-gauge
time-series data for that region/time-span, and report the findings. The
useful thing about this example is that it's a *mixed-determinism*
pipeline, not a uniformly fuzzy one — only part of it actually needs an
agent.

**Mapping the steps onto the three skills:**

1. **Storm name → characteristics** (web lookup, interpretation) — needs
   an `agent-runner` step. The only step that's genuinely fuzzy/
   reasoning-shaped; nothing here is scriptable without an agent's
   judgment and web access.
2. **Characteristics → region + time-span** — still agent-driven (turning
   "Katrina" into a precise bounding box + date range is itself a
   judgment call: storm track vs. landfall vs. area of damage vs. which
   coastline is actually tide-gauge-relevant aren't the same answer), but
   its *output* should be a small, structured artifact (e.g. a
   `region_timespan.json` with a bbox and a date range) — not free text
   handed to the next step.
3. **Region + time-span → tide-gauge time series** — fully deterministic:
   given an explicit bbox and dates, querying a tide-gauge API (e.g. NOAA
   CO-OPS, GESLA) and downloading data is a normal, scriptable, testable
   `workflow` rule. No agent involved at all here.
4. **Report the findings** — `reporting`, straightforwardly: same shape as
   the active-learning example already built for that skill (summary/
   methods/results/discussion, a figure, a judgment call about what story
   to tell).

**What this clarifies about the tensions below:**

- **Partially resolves the non-determinism tension**: don't try to make
  the agent step itself reproducible — instead, once steps 1-2 produce
  `region_timespan.json`, treat it as *frozen*, the same conceptual role
  `templates/`/`data/` already play in `workflow`'s structural categories
  (input later rules build on, not something casually regenerated).
  Snakemake shouldn't feel free to silently rerun the storm-lookup step
  and get a different bounding box on a whim — re-running it is an
  explicit human decision, not an automatic consequence of a downstream
  rule needing its output. This is a concrete rule worth keeping, not
  just "it's non-deterministic, shrug."
- **Sharpens the vendor-agnostic tension into something concrete**: step 1
  needs *web search/fetch* specifically, not just "any agent, any model."
  Different CLIs have different tool access (e.g. Claude Code's
  WebSearch/WebFetch vs. whatever another CLI offers or lacks). **Decided
  for v1: no upfront capability negotiation — just launch the agent and
  see if the step works.** The pipeline clearly won't work for just any
  agent, and the result will depend on which one ran it; that's accepted
  for now rather than solved. Capability *discovery* (e.g. an actual probe
  step that tests whether web access is available before relying on it)
  is explicitly future work, not v1 — see "Not yet decided" below.
- **Surfaces a real fork on where the agent sits**: "the user says
  Katrina and starts the entire workflow" implies an *outer* agent
  interpreting the raw utterance and kicking off the pipeline — which may
  or may not be the same agent session as the *inner* rule doing the
  actual storm lookup. Not decided whether this is one agent wearing two
  hats (conversational entry point + pipeline step, same session) or two
  architecturally distinct touchpoints (a thin outer launcher, a separate
  inner agent-as-rule). Partial answer, decided: when they are distinct,
  the inner agent defaults to the same vendor as the outer one — see
  "Known tensions" below for the reasoning.

## Worked example 2: an eval harness, built from `agent-runner` itself

**Status: built and actually run.** See `skill_tests/` at the
repo root, and "Confirmed by actually running it" below for what that run
found.

A second concrete use case — testing *other skills* (`workflow`,
`reporting`, `local-library`, any skill, not just `agent-runner`'s own
scripts) by actually running an agent against them. This directly closes
the "Testability" tension below and the item `plan.md`'s own "Testing"
section already flagged and left open ("formalizing this further ... is a
future option, not started") — `agent-runner`'s core capability (launch a
controlled agent session) turns out to be exactly what that formalization
needs, so this eval harness doubles as `agent-runner`'s own best proof of
concept once it exists.

**Mechanism**: one prompt pair per test case — a *subject* prompt that
exercises a skill, and a *judge* prompt that verifies the result — two
`agent-runner` invocations per case, wired into a `workflow` pipeline:

```
data/test_cases.yaml        # list of {name, first: <subject prompt>, second: <judge prompt>}
  ↓
split_test_cases               # like split_expressions.py — one scratch/<case>/ per row
  ↓
run_subject (per case)           # agent-runner, prompt.first, agent + skill under test, writes into scratch/<case>/run/
  ↓
judge_result (per case)            # agent-runner, prompt.second, cwd = scratch/<case>/run/
  ↓
collect_results                      # like collect_results.py — aggregate verdicts → outputs/
```

This reuses, exactly, the rule shape already built and tested in
`workflow_design.md`'s expression-evaluator example (split → per-case
compute → collect) — same pattern, prompt pairs instead of math
expressions. That it maps this cleanly onto something already proven to
work is itself a good sign for the design.

**Decided in discussion:**

- **The rubric lives inside `prompt.second` itself**, not a separate
  reference-answer field. If the judge's `agent-runner` invocation has its
  working directory set to the subject's output (`scratch/<case>/run/`),
  `prompt.second` can just be self-contained judging instructions ("verify
  this directory contains X, Y, Z; report PASS or FAIL with reasoning") —
  no path templating needed, nothing extra to author or keep in sync.
- **The judge should ideally be a different vendor than the subject**, to
  avoid correlated blind spots (see "Vendor-agnostic scope" below) — not
  required, but the obvious thing to try once vendor selection exists.
- **Verdict is structured, not a bare boolean** — pass/fail plus
  reasoning, so a failure is debuggable without needing to re-run it.

**Not yet decided**: whether `run_subject` leaves behind only the files it
produced, or also a transcript of what it *did* (tool calls, reasoning).
Final-state-only is simpler and matches the pipeline above directly; a
transcript lets the judge catch "right file, wrong reason," but is heavier
to capture and feed in. **Resolved for v1**: `run_subject` does save the
full transcript (`run-agent.py`'s own JSON output already includes it),
and the judge is told to read it directly — see below.

**Confirmed by actually running it — real bugs caught, not just designed
around.** Built as `skill_tests/` (via `init-workflow.py` +
`write_default_vendor_to_config` + the rule chain above), with one test
case: subject prompt "compute 6 * 7," judge prompt "check the transcript
says 42." Ran for real — both agent invocations, real cost ($0.0698 +
$0.1144 = $0.1842 total) — and got a correct `PASS` verdict with the
judge's own reasoning preserved in `outputs/eval_summary.txt`.

One real design bug was caught *before* spending any of that money, by
tracing through the mechanism rather than just running it: since the
judge's `cwd` is deliberately the same as the subject's output directory,
and `run-agent.py` always writes `agent_transcript.json` into whatever
`cwd` it's given, the judge's own run would silently **overwrite the
subject's transcript** — destroying the one thing the judge needs to
inspect, immediately after using it. Fixed by having `run_subject` copy
its transcript to a distinctly-named `subject_transcript.json` right
after the subject run, and pointing `prompt.second` at that name instead
of the (soon to be overwritten) default. Worth keeping in mind for any
future eval-harness refinement: whenever two steps deliberately share a
working directory, anything either step writes to a fixed, non-parameterized
filename is a collision waiting to happen.

**A second bug, caught by review rather than a fresh run**: the original
`collect_results.py` only read `judge_result.json`, so the summary could
only ever report the judge's own cost (verification overhead) — never the
subject's (the cost of the actual task under test, the more meaningful
number). Fixed by having the rule depend on both result files and the
summary report both, subject cost first. Verified for free, without
spending more real agent cost: fed the fixed script synthetic JSON
matching the real run's actual schema and values via a stub `snakemake`
object, rather than re-running the whole pipeline just to check a
reporting change.

**What this doesn't replace**: the pytest suite under `python_unit_tests/` (see
`plan.md`'s "Testing" section). This is slower, costlier (real agent +
judge sessions per case), and non-deterministic, so it's a periodic,
heavier-cadence check, not something run on every script change. It also
inherits `agent-runner`'s own non-determinism problem one level up: a
single pass/fail from one run isn't fully trustworthy given agent
non-determinism — probably wants a pass-rate-over-N-runs framing
eventually, not a one-shot boolean.

## Known tensions, surfaced in discussion but not resolved

- **Non-determinism vs. Snakemake's reproducibility model.** `workflow`'s
  `scratch/`-is-regenerable premise assumes rerunning a rule gives an
  equivalent result; an agent session doesn't guarantee that. "Success"
  for an agent step isn't just "the output file exists" the way it is for
  a deterministic computation — needs its own notion of a completion
  marker, not inherited wholesale from the rest of that skill's model.
  Partially clarified by the worked example above: freeze an agent step's
  structured output once produced, rather than treating it as freely
  regenerable the way a deterministic rule's output is.
- **Vendor-agnostic scope.** Each agent CLI differs in config, auth, and
  capabilities. A wrapper risks either flattening to the lowest common
  denominator (losing what makes a given agent worth choosing) or
  ballooning in complexity trying not to — this repo's own README already
  documents a version of this same tension for skill *installation*
  itself (native plugin marketplaces per agent, three incompatible
  manifest formats). **Resolved for v1, per the worked example**: don't
  solve capability matching upfront — launch whichever agent is
  configured and see if the step actually works; results will vary by
  agent, and that's an accepted v1 limitation, not a blocker. Formal
  capability *discovery* (e.g. a probe step that actually tests whether
  web access works before a pipeline relies on it) is real future work,
  deliberately deferred past v1.

  **Also implemented, same spirit**: a `settings["size"]`/`--size`
  `small`/`medium`/`large` alias, translated per-vendor (`haiku`/`sonnet`/
  `opus` for Claude Code), for callers that want a reasonable default
  without needing to know this vendor's specific names. Explicitly *not*
  claimed to be a validated cross-vendor equivalence — there's only one
  adapter to check it against — and not trying to cover every model (e.g.
  `fable` doesn't fit a size scheme and stays reachable only via
  `settings["model"]` directly). The justification mirrors the
  "just launch and see" stance above: it doesn't need to be perfect if
  nobody's optimizing for a specific agent, and for a small workflow that
  optimization doesn't pay off anyway. `--model`/`settings["model"]`
  always wins if both are given — the escape hatch stays available, this
  is a convenience default layered on top of it, not a replacement.
- **Outer vs. inner agent.** Not decided whether a natural-language
  trigger ("Katrina") and the in-pipeline research step are the same
  agent session wearing two hats, or two distinct touchpoints — see the
  worked example above. Affects the whole shape of the Python layer's
  interface, so worth resolving before designing it, not after. **Partial
  answer, decided**: when they *are* distinct, the inner (nested) agent
  defaults to the same vendor as the outer one. Consistent with "just
  launch and see if it works" above — the outer agent's vendor is already
  a known-working, authenticated instance in that session, so it's the
  safest default precisely because there's no capability negotiation yet.
  Stays overridable (the vendor-agnostic goal isn't abandoned, same-vendor
  is just the zero-config default).

  **How the layer learns the outer vendor — confirmed by testing, not
  just speculated.** Running `env | grep -i claude` inside an actual
  Claude Code session shows it already sets a clean set of identifying
  environment variables for every shell command it runs, no cooperation
  needed from the script being invoked:

  ```
  CLAUDECODE=1
  CLAUDE_CODE_SESSION_ID=4c530134-0b38-...
  CLAUDE_CODE_ENTRYPOINT=cli
  CLAUDE_CODE_EXECPATH=/root/.local/share/claude/versions/2.1.222
  AI_AGENT=claude-code_2-1-222_agent
  CLAUDE_CODE_CHILD_SESSION=1
  ```

  `CLAUDECODE=1` is exactly the kind of minimal boolean marker this
  mechanism needs, and it's already there today — auto-detection via a
  small set of known vendor env vars (rather than PATH search or process-
  tree inspection) looks like the right default mechanism, propagating
  naturally through however many process hops a shell spawns (still
  visible several layers deep through e.g. Snakemake). Not yet confirmed
  whether Codex/Copilot/other target CLIs set an equally clean marker —
  worth checking before leaning on this as *the* mechanism rather than
  one that happens to work cleanly for one vendor.

  **A more interesting lead: `CLAUDE_CODE_CHILD_SESSION=1`.** This
  session was already flagged by Claude Code itself as a "child session"
  — meaning Claude Code already has some built-in, vendor-native notion of
  nested/child sessions. Worth investigating what that actually means and
  whether `agent-runner` could piggyback on it (at least for this vendor)
  rather than inventing outer/inner session tracking from scratch — not
  yet understood, just noticed.

  **Resolved: starting a workflow without a live agent session at all.**
  Env-var detection only works when there's a live process to inspect —
  but `workflow`'s whole point is that a pipeline should be rerunnable
  later, unattended, with no agent wrapping it. So running `snakemake
  outputs/report.html` straight from a terminal (or cron, or CI), with no
  agent in sight, isn't an edge case to handle — it's the *normal* case
  for any already-scaffolded workflow, and the vendor mechanism has to
  work that way by default, not as a fallback:
  - **The vendor choice lives in `config.yaml`**, same as any other
    workflow parameter `workflow` already treats this way ("wire a config
    entry for anything that should be user-tunable without editing the
    rule itself") — e.g. `config["agent_vendor"] = "claude-code"`. Once
    it's there, it's just data in a file; no live session needs to exist
    for a rule to read it.
  - **Env-var auto-detection only runs once, at scaffold time** — when a
    rule needing `agent-runner` is first set up (presumably by whichever
    agent is helping build the workflow), its own `CLAUDECODE`-style
    marker becomes the default written into `config.yaml`. It is *not*
    re-detected on every later `snakemake` invocation.
  - **Fallback order when a vendor is genuinely unset**: `config.yaml`/
    `--config` override (explicit, wins) → env-var auto-detect (covers
    "run from inside a live agent's shell, but config wasn't set yet") →
    a clear, actionable error naming exactly what's missing. Never a
    silent PATH-search guess or an arbitrary default.
  - This also separates two questions that were previously conflated:
    *which agent helped scaffold this workflow* (one-time, env-detected,
    baked into `config.yaml`) vs. *which agent runs each rule*
    (a config lookup at execution time, nothing live required).
- **Safety/blast-radius inside automated pipelines.** An agent step can
  take real actions (file edits, shell commands) — embedding that inside
  an automated workflow raises the stakes well past "this step is slow,"
  which is as far as `workflow`'s existing dry-run/confirm-before-running
  discipline currently goes. Likely needs its own, stronger convention
  (sandboxing, explicit scope limits, something between "ask before a
  long run" and "ask before anything this step might do").
- **Testability.** Hard to unit-test the way the other skills' scripts
  just were (see `plan.md`'s "Testing" section) — launching an
  open-ended agent session is the "skill itself" testing problem
  (scenario-based, not pytest-amenable) baked into the core of what this
  skill's scripts actually do, not just the orchestration around them.
  **Turned into an opportunity, not just a problem**: see "Worked example
  2" above — `agent-runner`'s own core capability is exactly what a
  subject-prompt/judge-prompt eval harness needs, so it can help test
  every *other* skill even while remaining hard to unit-test itself.
  **The one genuinely untestable path (a real nested agent launch) has
  now actually been run, not just mocked**: `python3 run-agent.py
  "Compute 1+1" --vendor claude-code` launched a real `claude -p` session
  and got back `"result": "2"` — confirming vendor resolution, command
  construction, JSON parsing, and transcript capture all work end-to-end
  against the real CLI (cost ~$0.06, ~1.3s). This doesn't change the
  general tension (one successful smoke test isn't a test *suite*, and
  the non-determinism concern remains real for anything less trivial than
  "compute 1+1"), but it's no longer a purely theoretical gap.
- **Credential/settings handling.** "The Python layer controls settings"
  implies handling API keys/auth for whichever agent is launched — a real
  security surface, worth being deliberate about from the start rather
  than an afterthought.

  **Confirmed by testing: model selection can leak in via inherited
  environment, not just `--model`.** `ClaudeCodeAdapter.run()` calls
  `subprocess.run(cmd, cwd=cwd, ...)` without overriding `env=`, so the
  nested `claude -p` process inherits the *entire* environment of
  whatever launched it. Tested directly: running with `ANTHROPIC_MODEL=
  claude-fable-5` set in the parent shell — no `--model` flag passed —
  the nested session actually attempted Fable 5 (confirmed by its own
  error text: *"...to keep using Fable 5 or /model to switch models"*),
  ran out of usage credits for that model, and fell back to
  `claude-haiku-4-5-20251001` automatically. `ANTHROPIC_MODEL` isn't
  documented in `claude --help` (no `--model`-adjacent "Environment
  Variables" section exists there), but it's real and it works — found
  only by testing, not by reading `--help`, settings.json (only had
  `{"theme": "dark"}`), or `claude doctor` (none of which mentioned it).

  This means model selection today has two independent paths that could
  silently conflict: the explicit `--model` flag (documented, deliberate)
  and `ANTHROPIC_MODEL` (undocumented, inherited by accident unless the
  caller's own shell happens not to have it set). Not yet decided which
  should win if both are present, or whether `launch_agent` should
  deliberately scrub/control the child's environment rather than passing
  it through wholesale — see "Not yet decided" below.

## Draft Python interface (v1 sketch)

A first sketch of what the module actually looks like, scoped small on
purpose — matches the "just try it and see" stance already decided rather
than trying to solve every tension above before writing code. Implemented
as `skills/agent-runner/scripts/run-agent.py` — see that file and
`skills/agent-runner/SKILL.md` for the real, current version; this is the
sketch that preceded it.

```python
def detect_vendor_from_env() -> str | None:
    """Check known vendor-marker env vars (CLAUDECODE=1, etc.) for the
    agent hosting the *current* live process, if any. None if nothing
    recognized - never falls back to PATH search."""
    ...

def resolve_vendor(explicit=None, config_path=None) -> str:
    """Fallback chain: explicit override > config.yaml's agent_vendor key
    > detect_vendor_from_env() > raise a clear, actionable error. Every
    launch call goes through this - nothing guesses on its own."""
    ...

@dataclass
class AgentRunResult:
    vendor: str
    exit_code: int
    cwd: str
    transcript_path: str | None
    structured_output: dict | None

def launch_agent(prompt, *, vendor=None, cwd=".", settings=None,
                  config_path=None, timeout=None) -> AgentRunResult:
    """Resolves the vendor, dispatches to that vendor's adapter, returns a
    structured result. Raises only on setup/launch failure (no resolvable
    vendor) - never just because the agent's own task failed; that's part
    of the result (exit_code), not an exception. A 'judge' run (see Worked
    example 2) is just a second call to this with cwd pointed at the
    subject run's output directory - no separate judge function needed."""
    ...

class ClaudeCodeAdapter:
    """v1's only vendor adapter. Flags confirmed via `claude --help`, not
    guessed: -p/--print for non-interactive output, --output-format json
    for a single structured result, --model/--permission-mode/
    --allowed-tools for settings."""
    ...

def write_default_vendor_to_config(config_path: Path) -> str | None:
    """Scaffold-time only, NOT re-run on every later invocation (see
    'Resolved: starting a workflow without a live agent session' above).
    Detects the vendor via env and writes it into config.yaml as the
    persisted default if the key isn't already set there."""
    ...
```

Deliberately out of scope for this sketch (and for v1): other vendors'
adapters (only Claude Code implemented — its CLI is what's actually
available to test against), settings beyond what `claude`'s own flags
already expose, and anything from "Safety/blast-radius" or "Credential
handling" below beyond relying on whatever auth is already configured in
the ambient environment.

## Not yet decided

- The skill's actual name (`agent-runner` is a placeholder).
- Which agent CLIs to target first.
- Outer vs. inner agent: one session wearing two hats, or two distinct
  touchpoints (thin outer launcher + separate inner agent-as-rule)? See
  the worked example above — this shapes the whole interface, so it's
  worth resolving early.
- What `CLAUDE_CODE_CHILD_SESSION=1` actually means and whether
  `agent-runner` could build on Claude Code's own apparent child-session
  concept instead of inventing its own — see "Known tensions" above.
- Whether other target CLIs (Codex, Copilot, ...) set an equally clean
  vendor-identifying env var, before relying on env-var auto-detection as
  the general mechanism rather than a Claude-Code-specific convenience.
- Which wins if `--model`/`settings["model"]` and an inherited
  `ANTHROPIC_MODEL` env var disagree, and whether `launch_agent` should
  deliberately control what environment the child process sees rather
  than inheriting the caller's wholesale — confirmed by testing that
  `ANTHROPIC_MODEL` really does influence the nested session even without
  `--model`, see "Known tensions" → "Credential/settings handling" above.
- What the Python layer's interface actually looks like — this document
  only captures the goals and one worked example so far, not a structure
  or API.

## Deferred past v1 (deliberately, not forgotten)

- **Capability discovery, beyond model names.** One narrow slice of this
  is no longer deferred — see "Model discovery: implemented, free" below.
  Everything else (web access, other tool capabilities, whether a
  *specific* model has remaining usage credits right now) still just
  launches the configured agent and sees if the step works — no upfront
  checking, no negotiation. Later, worth a real probe mechanism (e.g. run
  a cheap test task that confirms web access actually works before a
  pipeline depends on it) for the parts that genuinely need a live,
  costly check rather than a free, static one.

## Model discovery: implemented, free

Resolves part of the capability-discovery gap above, cheaply. Confirmed
by testing: Claude Code's own `/model` slash command works in non-
interactive `-p` mode too, and is processed **client-side with
`total_cost_usd: 0`** — no real API call — for both the plain listing
and an invalid-name query:

```
$ claude -p "/model" --output-format json
# "result": "Current model: Sonnet 5 (default)\nUsage: /model <name>.
#   Available: sonnet, opus, haiku, fable, best, sonnet[1m], opus[1m],
#   fable[1m], opusplan, default, or a full model ID."

$ claude -p "/model totally-bogus-model-xyz" --output-format json
# "result": "Model 'totally-bogus-model-xyz' not found"   (also free)
```

Implemented as `list_available_models()` in `run-agent.py`, exposed via
`--list-models` and wired into `launch_agent` itself: if a requested
`--model` turns out not to exist or isn't accessible, the available names
are fetched automatically and surfaced on `AgentRunResult.
available_models` / a "Hint:" line in CLI output — see `SKILL.md`'s
"Discovering available models."

**What this does and doesn't tell you — the distinction matters, found by
testing, not assumed.** This lists which model *names* the CLI
recognizes, not which ones currently have remaining usage credits —
those are different questions with different costs to answer. Confirmed
directly: `claude-fable-5` is a recognized, listed name that still failed
in practice from credit exhaustion (see the `ANTHROPIC_MODEL` finding
above). Live per-model availability (will *this* model actually succeed
*right now*) still needs a real, costly probe and remains deferred, per
"Capability discovery" above.

**A related bug this surfaced and fixed**: `claude -p --model <bad-name>
...` exits with code **0** even though it failed (`is_error: true` in the
JSON payload) — confirmed by testing. `launch_agent`'s and `main()`'s own
success/failure logic now checks `structured_output.is_error`, not just
the subprocess exit code; before this fix, a bad-model run would have
been silently reported as successful.
