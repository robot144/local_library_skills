#!/usr/bin/env python3
"""Dev wiring only - NOT the end-user install path (see README.md's
"Installation" section for that; it copies, since an installed skill
shouldn't drift when this repo changes). This symlinks every skill under
skills/ into each known agent's skill directory, so an agent's own skill
discovery finds them from any cwd inside this repo - e.g.
example_eval_workflow's nested agent-runner sessions - without a separate
copy to keep in sync. Safe to rerun: only touches symlinks (or, on
Windows without admin/Developer Mode, directory junctions) it owns, and
only when something under skills/ actually changed.
"""

import os
from pathlib import Path

IS_WINDOWS = os.name == "nt"
FILE_ATTRIBUTE_REPARSE_POINT = 0x400

# Each agent's own project-scoped skill directory, per its docs (checked
# 2026-10-25) - these move fast, re-verify if an agent stops picking skills
# up. No separate entry for github-copilot-cli: its docs
# (https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)
# list .github/skills, .claude/skills, or .agents/skills as equally valid,
# and it already gets the latter from antigravity-cli below. Antigravity
# (https://antigravity.google/docs/skills/), Codex CLI (project-scoped
# .codex/skills/, same convention as its user-wide ~/.codex/skills/),
# Mistral Vibe (https://docs.mistral.ai/vibe/code/cli/skills).
AGENT_SKILL_DIRS = {
    "claude-code": ".claude/skills",
    "antigravity-cli": ".agents/skills",
    "codex-cli": ".codex/skills",
    "mistral-vibe-cli": ".vibe/skills",
}


def skill_names(skills_dir: Path) -> list[str]:
    return sorted(
        p.name for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").exists()
    )


def owned_by(skills_dir: Path, link: Path) -> bool:
    return Path(os.path.realpath(link)).parent == skills_dir.resolve()


def is_link(path: Path) -> bool:
    """True for symlinks, and - on Windows, where os.symlink needs admin/Developer
    Mode - also for NTFS directory junctions, which make_link() falls back to."""
    if path.is_symlink():
        return True
    if IS_WINDOWS and path.is_dir():
        try:
            attrs = os.stat(path, follow_symlinks=False).st_file_attributes
        except (AttributeError, OSError):
            return False
        return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
    return False


def remove_link(path: Path) -> None:
    # Directory symlinks and junctions are reparse points, not real
    # directories - Windows requires rmdir (RemoveDirectoryW) to remove the
    # reparse point itself rather than unlink (DeleteFileW).
    if IS_WINDOWS:
        path.rmdir()
    else:
        path.unlink()


def make_link(source: Path, link: Path, target_dir: Path) -> None:
    if IS_WINDOWS:
        try:
            link.symlink_to(os.path.relpath(source, target_dir), target_is_directory=True)
            return
        except OSError:
            pass
        import _winapi

        _winapi.CreateJunction(str(source.resolve()), str(link))
    else:
        link.symlink_to(os.path.relpath(source, target_dir))


def sync_target(skills_dir: Path, target_dir: Path) -> list[str]:
    changes = []
    target_dir.mkdir(parents=True, exist_ok=True)
    names = skill_names(skills_dir)

    for name in names:
        source = skills_dir / name
        link = target_dir / name
        if is_link(link):
            if Path(os.path.realpath(link)) == source.resolve():
                continue
            remove_link(link)
            make_link(source, link, target_dir)
            changes.append(f"updated {link}")
        elif link.exists():
            changes.append(f"skipped {link} (exists, not a symlink)")
        else:
            make_link(source, link, target_dir)
            changes.append(f"linked {link} -> skills/{name}")

    for entry in sorted(target_dir.iterdir()):
        if entry.name in names or not is_link(entry):
            continue
        if owned_by(skills_dir, entry):
            remove_link(entry)
            changes.append(f"removed stale {entry}")

    return changes


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    skills_dir = repo_root / "skills"

    changes = []
    for rel_target in AGENT_SKILL_DIRS.values():
        changes += sync_target(skills_dir, repo_root / rel_target)

    print("\n".join(changes) if changes else "No changes.")


if __name__ == "__main__":
    main()
