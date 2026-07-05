#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_NAME="initiate_new_project"
INSTALL_BASE="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"
TARGET="$INSTALL_BASE/$SKILL_NAME"
timestamp="$(date +%Y%m%d%H%M%S)"
staging="$(mktemp -d "/tmp/${SKILL_NAME}-staging.XXXXXX")"
backup=""
old_target="$INSTALL_BASE/.${SKILL_NAME}.previous.${timestamp}"

cleanup() {
  rm -rf "$staging"
}
trap cleanup EXIT

require_path() {
  rel="$1"
  if [ ! -e "$staging/$SKILL_NAME/$rel" ]; then
    printf 'Missing staging path: %s\n' "$rel" >&2
    exit 1
  fi
}

mkdir -p "$INSTALL_BASE"
cp -R "$SKILL_ROOT" "$staging/$SKILL_NAME"

require_path "SKILL.md"
require_path "scripts"
require_path "templates"
require_path "references"

if ! command -v python3 >/dev/null 2>&1; then
  printf 'Missing dependency: python3 is required by %s\n' "$SKILL_NAME" >&2
  exit 1
fi

chmod +x "$staging/$SKILL_NAME/scripts/"*.sh
while IFS= read -r script; do
  if ! bash -n "$script" >/dev/null 2>&1; then
    printf 'Invalid staging script: %s\n' "$script" >&2
    exit 1
  fi
done < <(find "$staging/$SKILL_NAME/scripts" "$staging/$SKILL_NAME/templates/scripts" -type f -name '*.sh' -print)

if [ -e "$TARGET" ]; then
  backup="/tmp/${SKILL_NAME}-install-backup-${timestamp}"
  cp -R "$TARGET" "$backup"
fi

tmp_target="$INSTALL_BASE/.${SKILL_NAME}.installing.${timestamp}"
rm -rf "$tmp_target"
mv "$staging/$SKILL_NAME" "$tmp_target"
if [ -e "$TARGET" ]; then
  rm -rf "$old_target"
  mv "$TARGET" "$old_target"
fi
if ! mv "$tmp_target" "$TARGET"; then
  if [ -e "$old_target" ] && [ ! -e "$TARGET" ]; then
    mv "$old_target" "$TARGET"
  fi
  printf 'Install failed while replacing target: %s\n' "$TARGET" >&2
  exit 1
fi
if [ -e "$old_target" ]; then
  rm -rf "$old_target"
fi

printf 'Installed: %s\n' "$TARGET"
if [ -n "$backup" ]; then
  printf 'Backup: %s\n' "$backup"
fi
