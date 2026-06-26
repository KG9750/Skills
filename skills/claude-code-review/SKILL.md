---
name: claude-code-review
description: Use local Claude Code as an external reviewer from Codex. Trigger for Claude-only review when the user says Claude Code, claude, claude-code, cc 审查, cc审查, cc review, or cc-review. Trigger cross-review debate when the user says 交叉审查, 双向审查, cc debate, codex vs claude, 反驳式 review, or asks Codex and Claude Code to debate code, plans, diffs, PRs, tests, architecture, or repository risks.
---

# Claude Code Review

Use the bundled script to call the local Claude Code CLI. This skill has two modes:

- Claude-only review: use when the user asks for `cc 审查`, `cc审查`, `cc review`, or Claude Code's independent opinion.
- Cross-review debate: use when the user asks for `交叉审查`, `双向审查`, `cc debate`, `codex vs claude`, or a debate between Codex and Claude.

Keep Claude Code in review mode. Do not let Claude Code edit files unless the user explicitly asks for implementation after the review.

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

### Route the Request

- If the user says `cc 审查`, `cc审查`, `cc review`, or asks only for Claude Code's view, run Claude-only review.
- If the user says `交叉审查`, `双向审查`, `cc debate`, `codex vs claude`, or asks for debate/convergence, run cross-review debate.

### Claude-Only Review

1. Verify the target directory is the project the user wants reviewed.
2. Run `claude-code-review` from that directory, or pass `--target /absolute/path`.
3. Add `--scope diff`, `--scope branch`, `--scope repo`, or `--scope files` when the requested review scope is clear.
4. Add `--prompt "..."` for task-specific instructions, such as a security focus or a plan-review standard.
5. Treat Claude Code output as reviewer input, then synthesize the final answer in Codex's normal review format with concrete file and line references where available.

### Cross-Review Debate

Codex is the moderator and final adjudicator. Claude Code is the external challenger. Evidence, not either model's confidence, resolves disagreements.

1. Verify the target directory and scope.
2. Codex independently reviews the target first. Write concise notes with findings, uncertainties, and evidence to a temporary file.
3. Run Claude in challenge mode with the Codex notes:

```bash
target="/absolute/path/to/project"
codex_notes="$(mktemp /tmp/codex-review.XXXXXX)"
claude_challenge="$(mktemp /tmp/claude-challenge.XXXXXX)"
cat > "$codex_notes" <<'NOTES'
Finding:
Evidence:
Uncertainty:
NOTES
claude-code-review --target "$target" --scope diff --mode challenge --codex-notes "$codex_notes" --output "$claude_challenge"
```

4. Codex reads Claude's challenge, checks the relevant files/tests/contracts, and builds a disagreement ledger for unresolved high-value claims:

```text
Claim:
Codex position:
Claude position:
Evidence:
Missing evidence:
Current status: accepted / rejected / downgraded / unresolved
Next question:
```

5. If serious unresolved disagreements remain, run up to 2 narrow convergence rounds:

```bash
target="/absolute/path/to/project"
disagreements="$(mktemp /tmp/disagreements.XXXXXX)"
claude_converge="$(mktemp /tmp/claude-converge.XXXXXX)"
cat > "$disagreements" <<'LEDGER'
Claim:
Current status: unresolved
Next question:
LEDGER
claude-code-review --target "$target" --scope diff --mode converge --disagreements "$disagreements" --output "$claude_converge"
```

6. Stop convergence when there are no fatal/serious unresolved disagreements, remaining disagreements depend on user/product judgment, a round adds no new evidence, or Claude has been called 3 times total.
7. Emit an adjudicated report, not two pasted reviews.

Final report shape:

- Confirmed: issues both sides agree on or Codex verified.
- Accepted From Claude: Claude-raised issues Codex verified.
- Codex-Only: Codex-confirmed issues Claude missed.
- Rejected / Downgraded: claims rejected or reduced after checking evidence.
- Remaining Unresolved: only issues needing user decision or external facts, ideally no more than 3.

Do not restart a full review during convergence. Ask Claude only to resolve listed disagreements, provide stronger evidence, concede/downgrade, or state exactly what evidence would be needed. New findings may enter the final report only if they are critical blockers.

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

Challenge Codex's initial review in cross-review debate:

```bash
target="/absolute/path/to/project"
codex_notes="$(mktemp /tmp/codex-review.XXXXXX)"
claude_challenge="$(mktemp /tmp/claude-challenge.XXXXXX)"
cat > "$codex_notes" <<'NOTES'
Finding:
Evidence:
Uncertainty:
NOTES
claude-code-review --target "$target" --scope diff --mode challenge --codex-notes "$codex_notes" --output "$claude_challenge"
```

Converge unresolved disagreements:

```bash
target="/absolute/path/to/project"
disagreements="$(mktemp /tmp/disagreements.XXXXXX)"
claude_converge="$(mktemp /tmp/claude-converge.XXXXXX)"
cat > "$disagreements" <<'LEDGER'
Claim:
Current status: unresolved
Next question:
LEDGER
claude-code-review --target "$target" --scope diff --mode converge --disagreements "$disagreements" --output "$claude_converge"
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
- For cross-review debate, serious findings must have file, line, command, trace, contract, or explicit reasoning-chain evidence before they become confirmed findings.
- Treat Claude Code output as challenger input, not ground truth.
- If the Claude CLI is missing, first run `command -v claude`; on Homebrew macOS installs it may be at `/opt/homebrew/bin/claude`.
