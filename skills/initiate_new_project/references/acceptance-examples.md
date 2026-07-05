# Acceptance Examples

## Empty Project

Run initialization in an empty directory. It must create all entry files, docs directories, scripts, hook docs, and `docs/generated/project-directory.md`.

## Existing Project

Pre-create `AGENTS.md` and `CONTEXT.md`. Initialization must leave their contents unchanged, create missing files, and list existing files under `Skipped existing:`.

## Existing User Script

Pre-create `scripts/update-project-directory.sh` without the managed marker. Initialization must skip it, not execute it, and list it under `Manual action required:`.

Validation must fail with `Invalid:` for the unmanaged script, must not require `scripts/codex-project-directory-hook.sh`, and must not invoke the user-owned script indirectly.

## Existing Directory Index

Pre-create `docs/generated/project-directory.md` without the managed directory-index marker. Initialization must preserve it, report it under `Manual action required:`, and not overwrite it.

Validation must not mutate `docs/generated/project-directory.md`. If the managed update script exists, validation must classify the unmarked index under `Invalid:`.

## Broken Managed Script

Pre-create or modify a managed `scripts/update-project-directory.sh` with shell syntax errors. Initialization must not execute it blindly; it must report the issue under `Manual action required:` and exit non-zero after printing all report sections.

## Space Path

Run initialization and validation in a path containing spaces. Both must succeed.

## Git and Issue Side Effects

Run initialization in a directory that is not a Git repository. It must not run `git init`, create `.gitignore`, create branches, add files, commit, tag, set remotes, push, create a GitHub repository, or create GitHub issues.

Run initialization in an existing Git repository. It may preserve and document the existing project structure, but it must not mutate Git state or publish issue-tracker content.

When the user asks for issue-driven development, the skill must route requirements into local PRD/spec/plan documents first and require explicit confirmation before invoking issue-oriented skills or creating external issues.

## Validator Failures

Remove a required path, remove execute permission from a script, or introduce shell syntax errors. Validator must return non-zero and classify the problem.
