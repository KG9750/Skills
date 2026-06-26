---
name: claude-code-review
description: Use local Claude Code as an external independent reviewer from Codex. Trigger when the user asks to use Claude Code, claude, claude-code, cc审查, cc review, or cc-review for code review, plan review, PR/diff review, adversarial review, second-opinion review, or to audit a repository without manually finding the Claude Code install path.
---

# Claude Code Review

Use the bundled script to call the local Claude Code CLI. This skill is for independent review only; do not let Claude Code edit files unless the user explicitly asks for implementation after the review.

## Quick Start

From the repository or project directory under review:

```bash
claude-code-review
```

Equivalent explicit script path:

```bash
skills/claude-code-review/scripts/claude-code-review
```

Short alias, if present:

```bash
cc-review
```

## Workflow

1. Verify the target directory is the project the user wants reviewed.
2. Run `claude-code-review` from that directory, or pass `--target /absolute/path`.
3. Add `--scope diff`, `--scope branch`, `--scope repo`, or `--scope files` when the requested review scope is clear.
4. Add `--prompt "..."` for task-specific instructions, such as a security focus or a plan-review standard.
5. Treat Claude Code output as reviewer input, then synthesize the final answer in Codex's normal review format with concrete file and line references where available.

The wrapper runs Claude Code in `--bare` mode with `--effort low` by default to avoid slow default startup context on this machine. Use `--effort medium|high|xhigh|max` only when the review needs deeper reasoning and latency is acceptable.

## Command Examples

Review current uncommitted changes:

```bash
claude-code-review --scope diff
```

Review a repo from another Codex working directory:

```bash
claude-code-review --target "/path/to/project" --scope repo
```

Review specific files:

```bash
claude-code-review --scope files -- src/foo.ts tests/foo.test.ts
```

Ask for a stricter second opinion:

```bash
claude-code-review --scope diff --prompt "Focus on correctness, data loss, security, missing tests, and backwards compatibility. Ignore style-only issues."
```

Save raw Claude Code output for later comparison:

```bash
claude-code-review --scope branch --output /tmp/claude-review.md
```

Limit cost for a larger review:

```bash
claude-code-review --scope repo --max-budget-usd 1
```

For large plan reviews, split the plan into focused prompts such as schema, incremental flow, bot coverage, and release gate. Treat an empty output file as a failed review, not as approval.

## Safety Rules

- Prefer `--scope diff` for normal code-review requests.
- Keep Claude Code in review mode. The script runs with `--permission-mode plan` and tells Claude not to modify files.
- If Claude Code reports findings without enough evidence, verify the relevant files yourself before presenting them as confirmed.
- If the Claude CLI is missing, first run `command -v claude`; on Homebrew macOS installs it may be at `/opt/homebrew/bin/claude`.
