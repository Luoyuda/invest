#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

tmpdir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

echo "[1/7] package validation"
if [[ "${SKIP_PACKAGE_VALIDATION:-0}" == "1" ]]; then
  echo "skip package validation"
else
  bash scripts/validate_package.sh
fi

echo "[2/7] python compile"
python3 -m py_compile scripts/*.py

echo "[3/7] generate sector state"
python3 scripts/build_sector_metrics.py \
  --csv fixtures/sector-metrics.sample.csv \
  --output "$tmpdir/sector-metrics.latest.json"
python3 scripts/generate_sector_state.py \
  --input "$tmpdir/sector-metrics.latest.json" \
  --output "$tmpdir/sector-state.latest.json"

echo "[4/7] generate recommendation run"
python3 scripts/collect_catalysts.py \
  --csv fixtures/catalysts.sample.csv \
  --output "$tmpdir/catalysts.latest.json"
python3 scripts/generate_candidates.py \
  --stocks-csv fixtures/stocks.sample.csv \
  --sector-state "$tmpdir/sector-state.latest.json" \
  --output "$tmpdir/candidates.latest.json"
python3 scripts/generate_recommendation_run.py \
  --candidates "$tmpdir/candidates.latest.json" \
  --sector-state "$tmpdir/sector-state.latest.json" \
  --output "$tmpdir/latest.json"
python3 - "$tmpdir/latest.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["recommendations"][0]["name"] == "样例股份"
assert data["sector_anchors"][0]["name"] == "样例锚点"
PY

echo "[5/7] validate positive run"
bash scripts/validate_run.sh "$tmpdir/latest.json"

echo "[6/7] validate negative fixtures"
for fixture in \
  fixtures/run.invalid-low-activity-high.json \
  fixtures/run.invalid-0900-intraday.json \
  fixtures/run.invalid-predicted-unmarked.json \
  fixtures/run.invalid-limit-up-recommendation.json; do
  if bash scripts/validate_run.sh "$fixture" >/tmp/lobster-invalid.out 2>&1; then
    echo "ERROR: invalid fixture unexpectedly passed: $fixture" >&2
    cat /tmp/lobster-invalid.out >&2
    exit 1
  fi
done
rm -f /tmp/lobster-invalid.out

echo "[7/7] audit, feedback, weekly review"
python3 scripts/audit_run_sources.py "$tmpdir/latest.json" --output "$tmpdir/source-audit.json" --skip-network
python3 scripts/append_feedback.py \
  --run-id smoke-test \
  --failure-type sector_selection_error \
  --summary "smoke test feedback" \
  --output "$tmpdir/feedback-log.jsonl"
mkdir -p "$tmpdir/runs"
cp "$tmpdir/latest.json" "$tmpdir/runs/latest.json"
python3 scripts/replay_recommendations.py \
  --run "$tmpdir/latest.json" \
  --prices-csv fixtures/replay-prices.sample.csv \
  --output "$tmpdir/replay.latest.json"
python3 scripts/weekly_review.py \
  --runs-dir "$tmpdir/runs" \
  --feedback "$tmpdir/feedback-log.jsonl" \
  --output "$tmpdir/weekly-review.json"

echo "Smoke test passed"
