#!/usr/bin/env bash
set -euo pipefail

CODEX_BASE="${CODEX_HOME:-$HOME/.codex}"
DEST_DIR="${1:-$CODEX_BASE/skills/lobster-invest}"

if [[ ! -d "$DEST_DIR" ]]; then
  echo "ERROR: installed directory not found: $DEST_DIR" >&2
  exit 1
fi

required=(
  "$DEST_DIR/runtime/README.md"
  "$DEST_DIR/references/run-output-schema.md"
  "$DEST_DIR/scripts/validate_run.sh"
  "$DEST_DIR/scripts/generate_sector_state.py"
  "$DEST_DIR/scripts/generate_recommendation_run.py"
  "$DEST_DIR/scripts/smoke_test.sh"
  "$DEST_DIR/fixtures/candidates.valid.json"
)

for path in "${required[@]}"; do
  [[ -f "$path" ]] || {
    echo "ERROR: missing installed file: $path" >&2
    exit 1
  }
done

(cd "$DEST_DIR" && SKIP_PACKAGE_VALIDATION=1 bash scripts/smoke_test.sh)
