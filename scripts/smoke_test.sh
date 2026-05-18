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
python3 scripts/refresh_sector_state.py \
  --boards-dir "$tmpdir/market-data" \
  --metrics-output "$tmpdir/refreshed-sector-metrics.latest.json" \
  --state-output "$tmpdir/refreshed-sector-state.latest.json" \
  --health-output "$tmpdir/sector-refresh.latest.json" \
  --summary-output "$tmpdir/sector-refresh.latest.txt" \
  --lock-file "$tmpdir/sector-refresh.lock" \
  --fetch-timeout-sec 15 \
  --generate-timeout-sec 10 \
  --limit 5 \
  --metric-limit-per-kind 3
python3 - "$tmpdir/sector-refresh.latest.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["status"] in {"passed", "degraded", "degraded_stale_state"}
assert data["duration_sec"] < 60
PY
python3 scripts/run_task.py \
  --name smoke-sector-refresh \
  --timeout-sec 60 \
  --retries 0 \
  --health-output "$tmpdir/task-runs/smoke-sector-refresh.latest.json" \
  --summary-output "$tmpdir/task-runs/smoke-sector-refresh.latest.txt" \
  --success-marker "$tmpdir/task-runs/smoke-sector-refresh.last-success.json" \
  --lock-file "$tmpdir/task-runs/smoke-sector-refresh.lock" \
  -- python3 scripts/refresh_sector_state.py \
    --boards-dir "$tmpdir/task-market-data" \
    --metrics-output "$tmpdir/task-sector-metrics.latest.json" \
    --state-output "$tmpdir/task-sector-state.latest.json" \
    --health-output "$tmpdir/task-sector-refresh.latest.json" \
    --summary-output "$tmpdir/task-sector-refresh.latest.txt" \
    --lock-file "$tmpdir/task-sector-refresh.lock" \
    --fetch-timeout-sec 15 \
    --generate-timeout-sec 10 \
    --limit 5 \
    --metric-limit-per-kind 3
python3 - "$tmpdir/task-runs/smoke-sector-refresh.latest.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["status"] == "passed"
assert data["attempts"][0]["status"] == "passed"
PY

echo "[4/7] generate recommendation run"
python3 scripts/fetch_capital_flow.py \
  300308 \
  --provider auto \
  --days 20 \
  --output "$tmpdir/capital-flow.latest.json" \
  --require-results
python3 - "$tmpdir/capital-flow.latest.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["status"] in {"passed", "degraded"}
result = data["results"][0]
assert result.get("summary", {}).get("recent_5d_main_net_inflow_yi") is not None or result.get("realtime")
assert "provider_results" in result
PY
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
cat > "$tmpdir/answer-valid.md" <<'EOF'
## 样例回答

| A | B |
|---|---|
| 1 | 2 |

### 来源链接
1. fixture，https://example.com；支撑信息：样例。
EOF
python3 scripts/validate_answer_format.py "$tmpdir/answer-valid.md" --max-tables 5 >/tmp/lobster-answer-format.out 2>&1
python3 scripts/write_outbox_message.py \
  --input "$tmpdir/answer-valid.md" \
  --task smoke-test \
  --outbox-dir "$tmpdir/outbox/pending" \
  --max-tables 5 >/tmp/lobster-outbox.out 2>&1
python3 - "$tmpdir/outbox/pending" <<'PY'
import json
import sys
from pathlib import Path

items = sorted(Path(sys.argv[1]).glob("*.json"))
assert items, "missing outbox metadata"
data = json.loads(items[-1].read_text(encoding="utf-8"))
assert data["status"] == "pending"
PY
cat > "$tmpdir/answer-invalid.md" <<'EOF'
| A | B |
|---|---|
| 1 | 2 |

| A | B |
|---|---|
| 1 | 2 |

| A | B |
|---|---|
| 1 | 2 |

| A | B |
|---|---|
| 1 | 2 |

| A | B |
|---|---|
| 1 | 2 |

| A | B |
|---|---|
| 1 | 2 |
EOF
if python3 scripts/validate_answer_format.py "$tmpdir/answer-invalid.md" --max-tables 5 >/tmp/lobster-answer-format-invalid.out 2>&1; then
  echo "ERROR: answer with too many tables unexpectedly passed" >&2
  cat /tmp/lobster-answer-format-invalid.out >&2
  exit 1
fi
rm -f /tmp/lobster-answer-format.out /tmp/lobster-answer-format-invalid.out
rm -f /tmp/lobster-outbox.out
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
