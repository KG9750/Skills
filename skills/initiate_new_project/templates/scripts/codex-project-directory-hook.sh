#!/usr/bin/env bash
# initiate_new_project managed: codex-project-directory-hook v1
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

"$SCRIPT_DIR/update-project-directory.sh" "$ROOT"
