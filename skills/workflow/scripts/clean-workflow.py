#!/usr/bin/env python3
"""Empty a workflow's disposable/regenerable directories.

Two modes:
  (default)  scratch/ only - always safe, since it's fully regenerable
             from data/ + templates/ by rerunning the rules that produced it.
  --all      scratch/ + outputs/ + logs/ + Snakemake's own .snakemake/
             cache - also removes the kept-forever results and logs, so
             only use this once you're sure nothing in outputs//logs/ is
             still needed (e.g. already reviewed, committed, or exported
             elsewhere).

Each targeted directory is emptied and left in place (so the standing
folder structure survives), with a .gitkeep restored if it ends up empty
(scratch/ doesn't need one - it's gitignored wholesale, same as
init-workflow.py leaves it). A directory containing nothing but its own
.gitkeep is treated as already-empty, not something to report as cleaned.

Usage: python3 clean-workflow.py [path/to/workflow-root] [--all] [--dry-run]
Defaults to ./workflow if no path is given. --dry-run reports what would be
emptied without changing anything.
"""
import shutil
import sys
from pathlib import Path

DEFAULT_ROOT = "workflow"


def has_content(path: Path) -> bool:
    return path.is_dir() and any(p.name != ".gitkeep" for p in path.iterdir())


def empty_and_keep(path: Path, dry_run: bool) -> bool:
    """Remove everything inside path, then recreate it empty with a
    .gitkeep. Returns True if there was anything to remove."""
    if not has_content(path):
        return False
    if not dry_run:
        shutil.rmtree(path)
        path.mkdir()
        (path / ".gitkeep").touch()
    return True


def empty_cache(path: Path, dry_run: bool) -> bool:
    """Remove a directory outright, no recreation (e.g. Snakemake's own
    .snakemake/ - not part of the standing folder structure)."""
    if not path.is_dir():
        return False
    if not dry_run:
        shutil.rmtree(path)
    return True


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    clean_all = "--all" in args
    args = [a for a in args if a not in ("--dry-run", "--all")]
    root = Path(args[0] if args else DEFAULT_ROOT)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1
    root = root.resolve()

    cleaned = []
    if empty_and_keep(root / "scratch", dry_run):
        cleaned.append(root / "scratch")

    if clean_all:
        if empty_and_keep(root / "outputs", dry_run):
            cleaned.append(root / "outputs")
        if empty_and_keep(root / "logs", dry_run):
            cleaned.append(root / "logs")
        if empty_cache(root / ".snakemake", dry_run):
            cleaned.append(root / ".snakemake")

    label = "Would empty" if dry_run else "Emptied"
    if not cleaned:
        print("Nothing to clean - already empty.")
    else:
        for path in cleaned:
            print(f"{label}: {path.relative_to(root.parent)}")

    if clean_all:
        print(
            "\nNote: --all also empties outputs/ and logs/, which are "
            "meant to be kept - make sure nothing there is still needed "
            "before running this for real."
        )

    tag = "Dry run - nothing changed" if dry_run else "Done"
    print(f"\n{tag}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
