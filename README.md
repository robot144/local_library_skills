# local_library_skills

Skills for coding agents (e.g. Claude Code) to support a **local library**: a folder of documents you want an agent to search, read, reference, and work with directly on disk — no external service, no re-uploading files into a chat each time.

Each skill lives under `skills/<skill-name>/` with a `SKILL.md` describing when and how to use it, plus any scripts it needs. Drop this repo (or the specific skill directories you want) wherever your agent loads skills from, per that agent's own conventions.

## Skills

| Skill | Purpose |
|---|---|
| [`pdf-to-markdown`](skills/pdf-to-markdown/SKILL.md) | Convert a PDF into searchable markdown (local GPU/CPU OCR via marker-pdf) — for large, scanned, or formula-heavy PDFs where reading page-by-page isn't practical. |

## Status

Which skills have actually been exercised against which agent, not just assumed to work because the directory convention matches.

| Skill | claude-cli | codex-cli | copilot-cli | antigravity-cli | mistral-cli |
|---|---|---|---|---|---|
| `pdf-to-markdown` | Working | Not checked yet | Not checked yet | Not checked yet | Not checked yet |

### By OS

| Skill | Linux | macOS | Windows (native) | WSL |
|---|---|---|---|---|
| `pdf-to-markdown` | Working | Not checked yet | Not working | Not checked yet |

`pdf-to-markdown`'s scripts are bash — native Windows (cmd.exe/PowerShell) can't run a `.sh` file at all, hence "Not working" rather than "not checked yet" for that column specifically. WSL is the documented workaround (see the skill's own "Platform check" section) and would likely work since it's a real Linux environment, but that's untested, not assumed — hence its own separate "Not checked yet" rather than lumping it in with native Windows.

## Prerequisites

Prerequisites are per-skill, not repo-wide — each skill's own `SKILL.md` has the details (required vs. optional, what degrades gracefully if something's missing, install commands for anything not already in a CliCodingAgents container). See [`pdf-to-markdown`'s Prerequisites](skills/pdf-to-markdown/SKILL.md#prerequisites) for the one skill here so far.

What's *not* skill-specific: `git`/`gh` (used only to get a skill's files onto disk in the first place — see Installation below, not by the skills themselves once installed).

## Installation using gh (GitHub CLI)

> **A fast way to get up and running could be Running in a [CliCodingAgents](https://github.com/robot144/CliCodingAgents) **  This has `gh` and other prerequisites all preinstalled by default — Inside the contaiers: skip straight to the commands below, no version-checking or setup needed.

Requires GitHub CLI **v2.90.0+** (`gh skill`, shipped April 2026). Check with `gh --version`; if older or not yet installed, follow [cli.github.com](https://cli.github.com/)'s instructions for your platform — **don't just `apt install gh`** or similar from your distro's default repos, those can be months or years behind (GitHub's own docs warn some community-packaged Debian/Ubuntu builds are outdated enough to be broken). Use the official GitHub-maintained repo/package it links to instead, then re-check `gh --version`.

```bash
# Install a specific skill for Claude Code, this project only (default scope)
gh skill install robot144/local_library_skills pdf-to-markdown --agent claude-code

# Same, but available globally in every project
gh skill install robot144/local_library_skills pdf-to-markdown --agent claude-code --scope user

# Install every skill in this repo at once
gh skill install robot144/local_library_skills --all --agent claude-code
```

Confirmed: `gh skill install` doesn't preserve the executable bit on installed scripts (content is unaffected, just the permission). If a script's own usage docs assume it can be run directly (`scripts/foo.sh ...`) and that fails with "Permission denied", run it once via `bash scripts/foo.sh ...` instead — for `pdf-to-markdown` specifically, `bash scripts/install.sh` self-heals the executable bit on its own sibling scripts, so after that one `bash`-prefixed call, the rest of its documented commands work as written.

Omit `--agent` to install for GitHub Copilot (the default), or pass another supported agent (`cursor`, `codex`, `gemini-cli`, and 20+ others — see `gh skill install --help` or the [`gh skill install` manual](https://cli.github.com/manual/gh_skill_install) for the full flag reference). `--scope` defaults to `project` (current git repo); pass `--scope user` for a user-wide, cross-project install. This installs straight from GitHub — no local clone needed, unlike the manual steps below.

## Coding agent specific installation

Several agents (Claude Code, Codex CLI, Antigravity CLI) have their own native `plugin marketplace add` + `plugin install` mechanism, with very similar command syntax across all three. **We don't support this path yet** — despite the similar commands, each uses its own incompatible manifest format and directory convention, so "one manifest" isn't actually an option:

| Agent | Manifest(s) required | Location |
|---|---|---|
| Claude Code | `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json` | repo root + per-plugin |
| Codex CLI | `.agents/plugins/marketplace.json` + `.codex-plugin/plugin.json` | repo root + per-plugin |
| Antigravity CLI | single `plugin.json` (own `$schema`, no separate marketplace file) | plugin root |

None of these are shared — supporting all three natively means maintaining three separate, agent-specific manifest sets in parallel with the actual `skills/<name>/SKILL.md` content, which only `gh skill install` and the manual copy method (below) currently use directly, agent-agnostically. Until that's worth the upkeep, use one of those two instead — both already work today for every agent in scope.

## Manual Installation

### 1. Get the repo (any coding agent)

```bash
git clone https://github.com/robot144/local_library_skills.git
```

If `gh` is present, prefer [`gh skill install`](#installation-using-gh-github-cli) above instead of this manual path — a plain clone is only the right choice when you don't have (or don't want to rely on) `gh`. This step just gets the files onto disk — it doesn't wire anything into an agent yet. How you do that next depends on the agent.

### 2. Install a skill — Claude Code

Claude Code loads skills from a `skills/<skill-name>/SKILL.md` directory, either per-project (`.claude/skills/`) or globally for every project (`~/.claude/skills/`). Copy the skill you want into whichever scope fits:

```bash
# Project-scoped — only available in this repo
mkdir -p .claude/skills
cp -r local_library_skills/skills/pdf-to-markdown .claude/skills/

# Global — available in every project
mkdir -p ~/.claude/skills
cp -r local_library_skills/skills/pdf-to-markdown ~/.claude/skills/
```

That's a plain copy, not a symlink — re-run it to pick up updates after pulling changes in `local_library_skills`.

For other agents, consult that agent's own docs for where it looks for skills/tools and copy (or symlink) the relevant `skills/<skill-name>/` directory there instead.

## License

GPL-3.0 — see [LICENSE](LICENSE).
