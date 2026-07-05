# Hooks Boundary

This skill creates hook-ready scripts but does not configure Codex global hooks.

## Generated Hook Wrapper

`scripts/codex-project-directory-hook.sh`:

- Locates the project root relative to the script path.
- Calls `scripts/update-project-directory.sh`.
- Exits with the directory-index script status.

## Optional Wiring

Recommended Codex hook points, if the user later chooses to wire them manually:

- `user_prompt_submit`: refresh before Codex processes a user request.
- `stop`: refresh after Codex finishes a turn.

Do not edit `~/.codex/config.toml` or hook trust state in this skill.
