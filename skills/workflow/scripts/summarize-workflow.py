#!/usr/bin/env python3
"""Summarize a Snakemake workflow root: purpose (from CLAUDE.md), declared
rules (from rules/*.smk, cross-checked against the Snakefile's include:
lines), and per-case status inferred from scratch/, outputs/, and logs/
subdirectories - a quick "what's in here and is it in good shape" view. By
default this is pure directory/text introspection, so it works even before
`pixi install`. Pass --snakemake-summary TARGET for Snakemake's target-
specific generated-file status table.

Usage: python3 summarize-workflow.py [path/to/workflow-root]
       [--snakemake-summary TARGET]
Defaults to ./workflow if no path is given.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = "workflow"
RULE_RE = re.compile(r"^rule\s+(\w+)\s*:", re.MULTILINE)
INCLUDE_RE = re.compile(r'^\s*include:\s*["\'](?P<path>[^"\']+)["\']', re.MULTILINE)
CASE_DIRS = ("scratch", "outputs", "logs")


def get_purpose(root: Path) -> str:
    claude_md = root / "CLAUDE.md"
    if not claude_md.is_file():
        return "(no CLAUDE.md found)"
    for line in claude_md.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "(no title line found in CLAUDE.md)"


def declared_rules(root: Path):
    """Maps rule name -> the rules/*.smk file (relative to root) it's
    declared in."""
    rules = {}
    rules_dir = root / "rules"
    if not rules_dir.is_dir():
        return rules
    for smk in sorted(rules_dir.glob("*.smk")):
        text = smk.read_text(encoding="utf-8")
        for m in RULE_RE.finditer(text):
            rules[m.group(1)] = smk.relative_to(root)
    return rules


def included_rule_files(root: Path):
    snakefile = root / "Snakefile"
    if not snakefile.is_file():
        return set()
    text = snakefile.read_text(encoding="utf-8")
    return {m.group("path") for m in INCLUDE_RE.finditer(text)}


def immediate_subdirs(path: Path):
    if not path.is_dir():
        return set()
    return {p.name for p in path.iterdir() if p.is_dir()}


def top_level_file_count(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for p in path.iterdir() if p.is_file() and p.name != ".gitkeep")


def snakemake_summary(root: Path, target: str) -> int:
    """Print Snakemake's generated-file status for one explicit target."""
    try:
        completed = subprocess.run(
            ["pixi", "run", "snakemake", "--summary", target],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        print(
            "error: '--snakemake-summary' requires the 'pixi' command",
            file=sys.stderr,
        )
        return 1

    print(f"\nSnakemake generated-file status (target: {target}):")
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    if completed.returncode:
        print(
            f"error: Snakemake summary failed with exit code {completed.returncode}",
            file=sys.stderr,
        )
    return completed.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=DEFAULT_ROOT)
    parser.add_argument(
        "--snakemake-summary",
        metavar="TARGET",
        help="also run 'pixi run snakemake --summary TARGET' in the workflow root",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1
    root = root.resolve()

    print(f"Workflow: {get_purpose(root)}")
    print(f"Root: {root}")

    rules = declared_rules(root)
    included = included_rule_files(root)
    print(f"\nRules ({len(rules)} declared in rules/):")
    for name, smk_path in sorted(rules.items()):
        flag = "" if str(smk_path) in included else "  <- NOT included in Snakefile"
        print(f"  {name}  ({smk_path}){flag}")
    for inc in sorted(included):
        if not (root / inc).is_file():
            print(f"  NOTE: Snakefile includes '{inc}', which doesn't exist")

    print("\nFolders:")
    case_names = set()
    for name in CASE_DIRS:
        subdirs = immediate_subdirs(root / name)
        files = top_level_file_count(root / name)
        case_names |= subdirs
        if subdirs:
            print(f"  {name}/: {len(subdirs)} case folder(s)")
        elif files:
            print(f"  {name}/: {files} file(s), flat (no per-case folders)")
        else:
            print(f"  {name}/: empty")

    if case_names:
        # Only cross-check against folders that actually use per-case
        # subfolders - a flat/aggregated folder (e.g. one rule collecting
        # every case into a single combined file) isn't "missing" any
        # given case just because it has no subfolder named after it.
        per_case_dirs = [name for name in CASE_DIRS if immediate_subdirs(root / name)]
        flat_dirs = [
            name
            for name in CASE_DIRS
            if name not in per_case_dirs and top_level_file_count(root / name)
        ]
        print(f"\nCases ({len(case_names)}), by presence in {'/'.join(per_case_dirs)}:")
        if flat_dirs:
            print(f"  (not checked per-case - flat/aggregated: {', '.join(flat_dirs)}/)")
        for case in sorted(case_names):
            presence = {
                name: case in immediate_subdirs(root / name) for name in per_case_dirs
            }
            marks = " ".join(
                f"{name}={'y' if present else 'n'}" for name, present in presence.items()
            )
            flag = ""
            if presence.get("scratch") and "outputs" in presence and not presence["outputs"]:
                flag = "  <- ran but no kept output yet"
            print(f"  {case}: {marks}{flag}")

    if args.snakemake_summary:
        return snakemake_summary(root, args.snakemake_summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
