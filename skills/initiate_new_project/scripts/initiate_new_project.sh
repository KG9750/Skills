#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s <project-root>\n' "$(basename "$0")" >&2
}

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_ROOT="$SKILL_ROOT/templates"

TARGET_INPUT="$1"
mkdir -p "$TARGET_INPUT"
PROJECT_ROOT="$(cd "$TARGET_INPUT" && pwd -P)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"

if ! command -v python3 >/dev/null 2>&1; then
  printf 'Missing dependency: python3 is required for template rendering\n' >&2
  exit 1
fi

if [ ! -d "$TEMPLATE_ROOT" ]; then
  printf 'Missing: templates directory %s\n' "$TEMPLATE_ROOT" >&2
  exit 1
fi

created_file="$(mktemp)"
skipped_file="$(mktemp)"
generated_file="$(mktemp)"
manual_file="$(mktemp)"
directory_status_file="$(mktemp)"
trap 'rm -f "$created_file" "$skipped_file" "$generated_file" "$manual_file" "$directory_status_file"' EXIT
init_error=0

note_created() { printf '%s\n' "$1" >> "$created_file"; }
note_skipped() { printf '%s\n' "$1" >> "$skipped_file"; }
note_generated() { printf '%s\n' "$1" >> "$generated_file"; }
note_manual() { printf '%s\n' "$1" >> "$manual_file"; }

is_managed() {
  file="$1"
  [ -f "$file" ] && grep -q 'initiate_new_project managed' "$file" 2>/dev/null
}

ensure_dir() {
  rel="$1"
  if [ ! -d "$PROJECT_ROOT/$rel" ]; then
    mkdir -p "$PROJECT_ROOT/$rel"
    note_created "$rel/"
  fi
}

render_template() {
  rel="$1"
  src="$TEMPLATE_ROOT/$rel"
  dst="$PROJECT_ROOT/$rel"

  if [ -e "$dst" ]; then
    note_skipped "$rel"
    return 1
  fi

  mkdir -p "$(dirname "$dst")"
  python3 - "$src" "$dst" "$PROJECT_NAME" "$PROJECT_ROOT" <<'PY'
import pathlib
import sys

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
project_name = sys.argv[3]
project_root = sys.argv[4]

text = src.read_text()
text = text.replace("{{PROJECT_NAME}}", project_name)
text = text.replace("{{PROJECT_ROOT}}", project_root)
dst.write_text(text)
PY
  note_created "$rel"
  return 0
}

dirs=(
  "docs/design-docs"
  "docs/exec-plans/active"
  "docs/exec-plans/completed"
  "docs/generated"
  "docs/product-specs"
  "docs/references"
  "scripts"
)

for dir in "${dirs[@]}"; do
  ensure_dir "$dir"
done

files=(
  "AGENTS.md"
  "CONTEXT.md"
  "DESIGN.md"
  "FRONTEND.md"
  "PLANS.md"
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

update_created=0
hook_created=0
for file in "${files[@]}"; do
  if render_template "$file"; then
    case "$file" in
      scripts/update-project-directory.sh)
        chmod +x "$PROJECT_ROOT/$file"
        update_created=1
        ;;
      scripts/codex-project-directory-hook.sh)
        chmod +x "$PROJECT_ROOT/$file"
        hook_created=1
        ;;
    esac
  fi
done

update_script="$PROJECT_ROOT/scripts/update-project-directory.sh"
hook_script="$PROJECT_ROOT/scripts/codex-project-directory-hook.sh"

update_unmanaged=0
if [ -f "$update_script" ] && ! is_managed "$update_script"; then
  update_unmanaged=1
fi

if [ "$update_unmanaged" -eq 1 ]; then
  if [ -e "$hook_script" ]; then
    note_skipped "scripts/codex-project-directory-hook.sh"
  else
    note_manual "scripts/codex-project-directory-hook.sh not created because update-project-directory.sh is user-owned"
  fi
else
  if render_template "scripts/codex-project-directory-hook.sh"; then
    chmod +x "$hook_script"
    hook_created=1
  fi
fi

if [ -f "$update_script" ] && [ ! -x "$update_script" ] && is_managed "$update_script"; then
  chmod +x "$update_script"
fi
if [ -f "$hook_script" ] && [ ! -x "$hook_script" ] && is_managed "$hook_script"; then
  chmod +x "$hook_script"
fi

if [ -f "$update_script" ] && is_managed "$update_script"; then
  if ! bash -n "$update_script" >/dev/null 2>&1; then
    note_manual "scripts/update-project-directory.sh has shell syntax errors; not executed"
    init_error=1
  elif PROJECT_DIRECTORY_STATUS_FILE="$directory_status_file" "$update_script" "$PROJECT_ROOT"; then
    directory_status="$(cat "$directory_status_file" 2>/dev/null || true)"
    case "$directory_status" in
      generated)
        note_generated "docs/generated/project-directory.md"
        ;;
      unchanged)
        note_skipped "docs/generated/project-directory.md"
        ;;
      skipped-unmanaged)
        note_manual "docs/generated/project-directory.md exists without managed marker; not overwritten"
        ;;
      *)
        note_manual "scripts/update-project-directory.sh did not report generation status"
        init_error=1
        ;;
    esac
  else
    note_manual "scripts/update-project-directory.sh failed during managed generation; run validator for details"
    init_error=1
  fi
else
  note_manual "scripts/update-project-directory.sh exists without managed marker; not executed"
fi

if [ -f "$hook_script" ] && ! is_managed "$hook_script"; then
  note_manual "scripts/codex-project-directory-hook.sh exists without managed marker; not executed"
fi

print_section() {
  label="$1"
  file="$2"
  printf '%s\n' "$label"
  if [ -s "$file" ]; then
    sed 's/^/- /' "$file"
  else
    printf -- '- none\n'
  fi
}

print_section "Created:" "$created_file"
print_section "Skipped existing:" "$skipped_file"
print_section "Generated:" "$generated_file"
print_section "Manual action required:" "$manual_file"

if [ "$init_error" -ne 0 ]; then
  exit 1
fi
