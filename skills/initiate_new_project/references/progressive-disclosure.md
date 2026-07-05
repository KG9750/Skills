# Progressive Disclosure

Use a small top-level surface and deeper task-specific documents.

## Entry Points

- `AGENTS.md`: agent-facing operating rules and navigation.
- `CONTEXT.md`: stable project context and boundaries.
- `DESIGN.md`: product and design entrypoint.
- `FRONTEND.md`: frontend implementation entrypoint.
- `PLANS.md`: execution-plan entrypoint.
- `docs/`: deeper project knowledge.

## Rules

- Keep entry files short and navigational.
- Put implementation details in the relevant subdirectory.
- Do not load generated indexes as source of truth; use them for orientation.
- Preserve existing project-specific entry files.

## New Project Discovery

Use `grill-me` when the project starts from a blank idea or has no reliable source docs. Use it to clarify user, goal, scope, constraints, success criteria, and tradeoffs.

Use `grill-with-docs` when the project already has project docs, PRDs, ADRs, legacy code, research notes, or domain terminology. Use it to challenge the plan against existing language and constraints.

## Result Placement

- `CONTEXT.md`: stable background, boundaries, terminology, current facts.
- `docs/product-specs/`: product goals, users, scope, requirements, flows.
- `docs/exec-plans/active/`: actionable implementation plans.
- `docs/design-docs/`: design principles and experience decisions.
- `docs/exec-plans/tech-debt-tracker.md`: rejected approaches, technical debt, deferred risks.

Keep raw interview notes out of the top level unless the user explicitly asks for an archive. Distill them into the durable layer they belong to.

## Issue Handoff

For projects that will move into development, keep the handoff progressive:

- Draft or update PRD-level requirements in `docs/product-specs/` before creating implementation issues.
- Put actionable local plans in `docs/exec-plans/active/`.
- Use issue-oriented skills such as `setup-matt-pocock-skills`, `to-prd`, or `to-issues` only when they are available and the user confirms issue-driven development.
- If no issue tracker is confirmed, keep issue candidates local rather than publishing them externally.
- Do not make Git, GitHub, or issue-tracker changes as part of documentation scaffolding.
