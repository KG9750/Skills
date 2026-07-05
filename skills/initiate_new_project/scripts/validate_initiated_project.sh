#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s <project-root>\n' "$(basename "$0")" >&2
}

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

TARGET_INPUT="$1"
if [ ! -d "$TARGET_INPUT" ]; then
  printf 'Missing:\n- %s\n' "$TARGET_INPUT"
  exit 1
fi

PROJECT_ROOT="$(cd "$TARGET_INPUT" && pwd -P)"
missing_file="$(mktemp)"
invalid_file="$(mktemp)"
not_exec_file="$(mktemp)"
runtime_file="$(mktemp)"
hook_stdout="$(mktemp)"
hook_stderr="$(mktemp)"
runtime_dir="$(mktemp -d)"
runtime_out="$runtime_dir/project-directory.md"
trap 'rm -f "$missing_file" "$invalid_file" "$not_exec_file" "$runtime_file" "$hook_stdout" "$hook_stderr"; rm -rf "$runtime_dir"' EXIT

required_paths=(
  "AGENTS.md"
  "CONTEXT.md"
  "DESIGN.md"
  "FRONTEND.md"
  "PLANS.md"
  "docs/design-docs"
  "docs/exec-plans/active"
  "docs/exec-plans/completed"
  "docs/generated"
  "docs/product-specs"
  "docs/references"
  "docs/README.md"
  "docs/design-docs/index.md"
  "docs/design-docs/core-beliefs.md"
  "docs/exec-plans/active/README.md"
  "docs/exec-plans/completed/README.md"
  "docs/exec-plans/tech-debt-tracker.md"
  "docs/generated/README.md"
  "docs/generated/project-directory-hooks.md"
  "docs/product-specs/index.md"
  "docs/product-specs/new-user-onboarding.md"
  "docs/references/README.md"
  "scripts/update-project-directory.sh"
)

for rel in "${required_paths[@]}"; do
  if [ ! -e "$PROJECT_ROOT/$rel" ]; then
    printf '%s\n' "$rel" >> "$missing_file"
  fi
done

scripts=(
  "scripts/update-project-directory.sh"
  "scripts/codex-project-directory-hook.sh"
)

is_managed() {
  file="$1"
  [ -f "$file" ] && grep -q 'initiate_new_project managed' "$file" 2>/dev/null
}

is_managed_directory_index() {
  file="$1"
  [ -f "$file" ] && grep -q 'initiate_new_project managed: project-directory' "$file" 2>/dev/null
}

for rel in "${scripts[@]}"; do
  path="$PROJECT_ROOT/$rel"
  if [ -e "$path" ]; then
    if [ ! -x "$path" ]; then
      printf '%s\n' "$rel" >> "$not_exec_file"
    fi
    if ! bash -n "$path" >/dev/null 2>&1; then
      printf '%s\n' "$rel" >> "$invalid_file"
    fi
  fi
done

hook="$PROJECT_ROOT/scripts/codex-project-directory-hook.sh"
update="$PROJECT_ROOT/scripts/update-project-directory.sh"
update_is_managed=0
if [ -e "$update" ] && is_managed "$update"; then
  update_is_managed=1
fi

if [ "$update_is_managed" -eq 1 ] && [ ! -e "$hook" ]; then
  printf 'scripts/codex-project-directory-hook.sh\n' >> "$missing_file"
fi

if [ -e "$hook" ] && ! is_managed "$hook"; then
  printf 'scripts/codex-project-directory-hook.sh (missing managed marker)\n' >> "$invalid_file"
fi
if [ -e "$update" ] && ! is_managed "$update"; then
  printf 'scripts/update-project-directory.sh (user-owned; managed validation skipped)\n' >> "$invalid_file"
fi

if [ -x "$hook" ] && [ -x "$update" ] && is_managed "$hook" && is_managed "$update"; then
  if ! PROJECT_DIRECTORY_OUT="$runtime_out" "$hook" >"$hook_stdout" 2>"$hook_stderr"; then
    printf 'scripts/codex-project-directory-hook.sh\n' >> "$runtime_file"
  elif ! is_managed_directory_index "$runtime_out"; then
    printf 'scripts/codex-project-directory-hook.sh (did not produce managed project-directory output)\n' >> "$runtime_file"
  fi
fi

project_directory="$PROJECT_ROOT/docs/generated/project-directory.md"
if [ "$update_is_managed" -eq 1 ]; then
  if [ ! -f "$project_directory" ]; then
    printf 'docs/generated/project-directory.md\n' >> "$missing_file"
  elif ! is_managed_directory_index "$project_directory"; then
    printf 'docs/generated/project-directory.md (missing managed marker)\n' >> "$invalid_file"
  elif ! grep -q '^# Project Directory Index$' "$project_directory" 2>/dev/null; then
    printf 'docs/generated/project-directory.md (missing expected heading)\n' >> "$invalid_file"
  fi
fi

print_if_any() {
  label="$1"
  file="$2"
  if [ -s "$file" ]; then
    printf '%s\n' "$label"
    sed 's/^/- /' "$file"
  fi
}

if [ -s "$missing_file" ] || [ -s "$invalid_file" ] || [ -s "$not_exec_file" ] || [ -s "$runtime_file" ]; then
  print_if_any "Missing:" "$missing_file"
  print_if_any "Invalid:" "$invalid_file"
  print_if_any "Not executable:" "$not_exec_file"
  print_if_any "Runtime error:" "$runtime_file"
  exit 1
fi

printf 'OK\n'
