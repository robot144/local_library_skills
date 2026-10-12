#!/usr/bin/env python3
"""Generate an exact Snakemake DOT DAG or a Mermaid Markdown rendering.

Usage: python3 render-workflow-dag.py [path/to/workflow-root] --target TARGET
       [--format dot|markdown] [--output PATH]

Defaults to ./workflow and Markdown output. Snakemake is run through the
workflow's local Pixi environment, so this requires a working pixi.toml and
installed dependencies.
"""
import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = "workflow"
NODE_RE = re.compile(r'^\s*(?P<id>\d+)\[label = "(?P<label>.*)", color =', re.MULTILINE)
EDGE_RE = re.compile(r"^\s*(?P<source>\d+) -> (?P<target>\d+)", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=DEFAULT_ROOT)
    parser.add_argument("--target", required=True, help="Snakemake target to visualize")
    parser.add_argument(
        "--format",
        choices=("dot", "markdown"),
        default="markdown",
        help="output format (default: markdown)",
    )
    parser.add_argument("--output", type=Path, help="write output to this file instead of stdout")
    return parser.parse_args()


def generate_dot(root: Path, target: str) -> str | None:
    try:
        completed = subprocess.run(
            ["pixi", "run", "snakemake", "--dag", target],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        print("error: DAG rendering requires the 'pixi' command", file=sys.stderr)
        return None

    if completed.returncode:
        if completed.stdout:
            print(completed.stdout, file=sys.stderr, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        print(f"error: Snakemake DAG generation failed with exit code {completed.returncode}", file=sys.stderr)
        return None
    return completed.stdout


def mermaid_markdown(dot: str, target: str) -> str:
    nodes = {match["id"]: match["label"] for match in NODE_RE.finditer(dot)}
    edges = [(match["source"], match["target"]) for match in EDGE_RE.finditer(dot)]
    if not nodes:
        raise ValueError("Snakemake emitted no DAG nodes")

    lines = [
        "# Workflow DAG",
        "",
        f"Target: `{target}`",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    for node_id, label in nodes.items():
        label = html.escape(label, quote=True).replace(r"\n", "<br/>")
        lines.append(f'    node_{node_id}["{label}"]')
    for source, destination in edges:
        lines.append(f"    node_{source} --> node_{destination}")
    lines.extend(["```", ""])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1
    root = root.resolve()

    dot = generate_dot(root, args.target)
    if dot is None:
        return 1

    try:
        rendered = dot if args.format == "dot" else mermaid_markdown(dot, args.target)
    except ValueError as error:
        print(f"error: could not convert Snakemake DAG to Mermaid: {error}", file=sys.stderr)
        return 1

    if args.output:
        if not args.output.parent.is_dir():
            print(f"error: output directory does not exist: {args.output.parent}", file=sys.stderr)
            return 1
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote {args.format} DAG: {args.output}")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
