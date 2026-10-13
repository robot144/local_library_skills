#!/usr/bin/env python3
"""Launch a coding agent session (Claude Code only, v1) from a script -
usable standalone or as a Snakemake `shell:`/`script:` step. Resolves
which agent vendor to use via a fixed fallback chain (explicit > config.yaml
> environment auto-detect > error), never guessing via PATH search.

This is a first version, deliberately scoped small - see
agent-runner_design.md for the full design, worked examples, and what's
still deferred (other vendor adapters, full capability discovery beyond
model names, credential handling beyond relying on the ambient
environment's own auth).

If a requested --model turns out not to exist or isn't accessible (exits
0 but sets is_error: true - confirmed by testing, not a safe thing to
infer from the exit code alone), the available model names are fetched
for free via Claude Code's own `/model` command and surfaced in the
result/CLI output - not a live per-model availability probe, just which
names are recognized.

Usage:
  python3 run-agent.py "<prompt>" [--vendor V] [--cwd DIR] [--model M]
      [--permission-mode MODE] [--config config.yaml] [--output result.json]
      [--timeout SECONDS]
  python3 run-agent.py --prompt-file p.txt ...        # read the prompt from a file instead
  python3 run-agent.py --detect-vendor                  # print the auto-detected vendor, or error
  python3 run-agent.py --write-default-vendor config.yaml   # scaffold-time only, see
                                                                # write_default_vendor_to_config()
  python3 run-agent.py --list-models                      # print available model names, free, no agent launch
"""
import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

# Parses Claude Code's own `/model` result text, e.g.:
#   "Current model: Sonnet 5 (default)\nUsage: /model <name>. Available:
#   sonnet, opus, haiku, fable, best, ... , or a full model ID."
# Confirmed by testing: `/model` (and `/model <bad-name>`) are processed
# client-side with total_cost_usd: 0 - free, no real API call - unlike a
# live per-model availability probe (see agent-runner_design.md's
# "Deferred past v1"). This tells you which model *names* are recognized,
# not whether a given one currently has remaining usage credits.
CURRENT_MODEL_RE = re.compile(r"Current model:\s*(.+)")
AVAILABLE_MODELS_RE = re.compile(r"Available:\s*(.+?)(?:,?\s*or a full model ID\.)?\s*$")

# Known env vars marking which agent vendor is hosting the *current* live
# process, if any - confirmed by testing (`env | grep -i claude` inside an
# actual Claude Code session), not guessed. Only Claude Code is covered in
# v1; add markers here as other vendors are actually targeted.
VENDOR_ENV_MARKERS = {
    "CLAUDECODE": "claude-code",
}

CONFIG_VENDOR_KEY = "agent_vendor"
DEFAULT_CONFIG_PATH = "config.yaml"


class VendorResolutionError(RuntimeError):
    pass


def detect_vendor_from_env() -> str | None:
    for var, vendor in VENDOR_ENV_MARKERS.items():
        if os.environ.get(var):
            return vendor
    return None


def read_config_vendor(config_path: Path) -> str | None:
    if not config_path.is_file():
        return None
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data.get(CONFIG_VENDOR_KEY)


def resolve_vendor(explicit: str | None = None, config_path: Path | None = None) -> str:
    """Fallback chain: explicit override > config.yaml's agent_vendor key >
    env auto-detect > a clear, actionable error. This is the only place
    vendor selection logic lives - nothing else should guess on its own."""
    if explicit:
        return explicit
    if config_path is not None:
        from_config = read_config_vendor(config_path)
        if from_config:
            return from_config
    detected = detect_vendor_from_env()
    if detected:
        return detected
    raise VendorResolutionError(
        f"No agent vendor specified and none could be resolved. Pass "
        f"--vendor explicitly, set '{CONFIG_VENDOR_KEY}' in config.yaml, "
        "or run this from inside a recognized agent session."
    )


@dataclass
class AgentRunResult:
    vendor: str
    exit_code: int
    cwd: str
    transcript_path: str | None
    structured_output: dict | None
    available_models: dict | None = None


def list_available_models(cwd=".") -> dict | None:
    """Free, zero-cost discovery via Claude Code's own `/model` command -
    see the module-level comment above CURRENT_MODEL_RE for what this does
    and doesn't tell you. Returns {"current": str, "available": [str,
    ...]}, or None if the call failed or the response couldn't be parsed
    (e.g. `claude` not on PATH, or a future CLI version changes the
    message format)."""
    try:
        completed = subprocess.run(
            ["claude", "-p", "/model", "--output-format", "json"],
            cwd=cwd, text=True, capture_output=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None

    text = data.get("result") or ""
    available_m = AVAILABLE_MODELS_RE.search(text)
    if not available_m:
        return None
    current_m = CURRENT_MODEL_RE.search(text)
    return {
        "current": current_m.group(1).strip() if current_m else None,
        "available": [m.strip() for m in available_m.group(1).split(",")],
    }


class ClaudeCodeAdapter:
    """v1's only vendor adapter. Flags confirmed via `claude --help`, not
    guessed: -p/--print for non-interactive output, --output-format json
    for a single structured result, --model/--permission-mode/
    --allowed-tools for settings."""

    # Vendor-agnostic size alias -> this vendor's own model name. A
    # deliberately "good enough, not perfect" mapping - not validated
    # across any other vendor (there isn't one implemented yet), and
    # doesn't try to cover every model this vendor has (e.g. `fable`
    # doesn't fit a small/medium/large scheme at all - it's reachable via
    # settings["model"] directly, not through this alias). The point is a
    # convenience default for callers that aren't optimizing for a
    # specific agent, not a precise cross-vendor equivalence - when a
    # workflow is small, that optimization doesn't pay off anyway.
    SIZE_ALIASES = {
        "small": "haiku",
        "medium": "sonnet",
        "large": "opus",
    }

    def build_command(self, prompt: str, settings: dict) -> list:
        cmd = ["claude", "-p", prompt, "--output-format", "json"]
        model = settings.get("model")
        if not model and settings.get("size"):
            size = settings["size"]
            if size not in self.SIZE_ALIASES:
                raise ValueError(
                    f"unknown size '{size}' (recognized: "
                    f"{', '.join(self.SIZE_ALIASES)}); pass settings['model'] "
                    "directly for anything else"
                )
            model = self.SIZE_ALIASES[size]
        if model:
            cmd += ["--model", str(model)]
        if "permission_mode" in settings:
            cmd += ["--permission-mode", str(settings["permission_mode"])]
        if settings.get("allowed_tools"):
            cmd += ["--allowed-tools", *settings["allowed_tools"]]
        return cmd

    def run(self, prompt: str, cwd: Path, settings: dict, timeout):
        cmd = self.build_command(prompt, settings)
        completed = subprocess.run(
            cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout
        )
        structured = None
        if completed.stdout:
            try:
                structured = json.loads(completed.stdout)
            except json.JSONDecodeError:
                structured = None

        available_models = None
        if structured and structured.get("is_error"):
            # Confirmed by testing: an invalid --model exits 0 but sets
            # is_error: true with api_error_status: 404 and a message
            # mentioning "model" - check both since only api_error_status
            # is precise, but a future CLI version's wording could change
            # while still being a model problem.
            result_text = (structured.get("result") or "").lower()
            if structured.get("api_error_status") == 404 or "model" in result_text:
                available_models = list_available_models(cwd)

        return completed.returncode, completed.stdout, completed.stderr, structured, available_models


VENDOR_ADAPTERS = {
    "claude-code": ClaudeCodeAdapter(),
}


def launch_agent(
    prompt: str,
    *,
    vendor: str | None = None,
    cwd="." ,
    settings: dict | None = None,
    config_path=None,
    timeout: int | None = None,
) -> AgentRunResult:
    """Resolves the vendor, dispatches to that vendor's adapter, returns a
    structured result. Raises only on setup/launch failure (no resolvable
    or implemented vendor) - never just because the agent's own task
    failed; that's part of the result (exit_code), not an exception.

    A "judge" run (see agent-runner_design.md's eval-harness worked
    example) is just a second call to this with cwd pointed at the
    subject run's output directory - no separate judge function needed."""
    resolved_config_path = Path(config_path) if config_path else Path(DEFAULT_CONFIG_PATH)
    v = resolve_vendor(vendor, resolved_config_path)
    if v not in VENDOR_ADAPTERS:
        raise VendorResolutionError(
            f"no adapter implemented for vendor '{v}' (available: "
            f"{', '.join(VENDOR_ADAPTERS)})"
        )

    cwd_path = Path(cwd)
    cwd_path.mkdir(parents=True, exist_ok=True)

    exit_code, stdout, stderr, structured, available_models = VENDOR_ADAPTERS[v].run(
        prompt, cwd_path, settings or {}, timeout
    )

    transcript_path = cwd_path / "agent_transcript.json"
    transcript_path.write_text(stdout or "", encoding="utf-8")
    if stderr:
        (cwd_path / "agent_stderr.log").write_text(stderr, encoding="utf-8")

    return AgentRunResult(
        vendor=v,
        exit_code=exit_code,
        cwd=str(cwd_path),
        transcript_path=str(transcript_path),
        structured_output=structured,
        available_models=available_models,
    )


def write_default_vendor_to_config(config_path: Path) -> str | None:
    """Scaffold-time only - run once, when a rule needing this script is
    first set up, NOT re-run on every later `snakemake` invocation (see
    agent-runner_design.md's "Resolved: starting a workflow without a live
    agent session"). Detects the vendor via env and writes it into
    config_path as the persisted default if the key isn't already set
    there. Returns the vendor written (or already present), or None if
    nothing detected and nothing already present."""
    existing = read_config_vendor(config_path)
    if existing:
        return existing
    detected = detect_vendor_from_env()
    if not detected:
        return None
    data = {}
    if config_path.is_file():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    data[CONFIG_VENDOR_KEY] = detected
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return detected


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", help="Prompt text (or use --prompt-file)")
    parser.add_argument("--prompt-file", help="Read the prompt from this file instead")
    parser.add_argument("--vendor", help="Explicit vendor override")
    parser.add_argument("--cwd", default=".", help="Working directory for the agent run")
    parser.add_argument("--config", help="config.yaml to read agent_vendor from (default: ./config.yaml)")
    parser.add_argument("--model", help="Vendor-specific model name/alias (wins over --size if both given)")
    parser.add_argument(
        "--size", choices=["small", "medium", "large"],
        help="Vendor-agnostic size alias, translated per-vendor (e.g. small -> haiku for "
        "Claude Code) - a convenience default, not a precise cross-vendor equivalence",
    )
    parser.add_argument("--permission-mode")
    parser.add_argument("--output", help="Write the AgentRunResult as JSON to this path")
    parser.add_argument("--timeout", type=int)
    parser.add_argument(
        "--detect-vendor", action="store_true",
        help="Print the auto-detected vendor and exit, don't launch anything",
    )
    parser.add_argument(
        "--write-default-vendor", metavar="CONFIG_PATH",
        help="Scaffold-time: write the detected vendor into this config.yaml if unset, then exit",
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="Print available model names (free, no agent launch) and exit",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.list_models:
        info = list_available_models()
        if not info:
            print("error: could not determine available models", file=sys.stderr)
            return 1
        print(f"Current default: {info['current']}")
        print("Available: " + ", ".join(info["available"]))
        return 0

    if args.write_default_vendor:
        vendor = write_default_vendor_to_config(Path(args.write_default_vendor))
        if vendor:
            print(f"agent_vendor: {vendor}")
            return 0
        print("error: no vendor detected and none already set", file=sys.stderr)
        return 1

    if args.detect_vendor:
        vendor = detect_vendor_from_env()
        if vendor:
            print(vendor)
            return 0
        print("error: no vendor detected from environment", file=sys.stderr)
        return 1

    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    elif args.prompt:
        prompt = args.prompt
    else:
        print("error: provide a prompt or --prompt-file", file=sys.stderr)
        return 1

    settings = {}
    if args.model:
        settings["model"] = args.model
    if args.size:
        settings["size"] = args.size
    if args.permission_mode:
        settings["permission_mode"] = args.permission_mode

    try:
        result = launch_agent(
            prompt,
            vendor=args.vendor,
            cwd=args.cwd,
            settings=settings,
            config_path=args.config,
            timeout=args.timeout,
        )
    except (VendorResolutionError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.output:
        Path(args.output).write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")

    print(f"vendor={result.vendor} exit_code={result.exit_code} transcript={result.transcript_path}")
    if result.available_models:
        print(
            f"Hint: the requested model may not exist or isn't accessible. "
            f"Current default: {result.available_models['current']}. "
            f"Available: {', '.join(result.available_models['available'])}"
        )
    structured_is_error = bool((result.structured_output or {}).get("is_error"))
    return 0 if result.exit_code == 0 and not structured_is_error else 1


if __name__ == "__main__":
    sys.exit(main())
