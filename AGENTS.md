# AGENTS.md

This workspace is intended to be used with CLI coding agents inside the Apptainer containers from `CliCodingAgents`.

## Workspace bootstrap defaults

- Python environments are managed with `pixi`.
- If no `pixi.toml` exists, the container bootstrap may create a minimal default one.
- If no `.pixi` environment exists yet, the bootstrap may run `pixi install`.
- The container bootstrap also installs `python` and `python3` shims in `$HOME/bin` that forward to `pixi run python`.

## Working assumptions for agents

- Prefer working with files in the current mounted project directory.
- Treat user files and local changes as authoritative; do not overwrite them casually.
- If an `AGENTS.md`, `pyproject.toml`, or `pixi.toml` already exists in the project, prefer that project-specific configuration over container defaults.

## Useful commands

```bash
pixi install
pixi run python script.py
pixi shell
```
