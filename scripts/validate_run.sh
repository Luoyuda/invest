#!/usr/bin/env bash
set -euo pipefail

RUN_FILE="${1:-runtime/recommendation-runs/latest.json}"

if [[ ! -f "$RUN_FILE" ]]; then
  echo "ERROR: missing run file: $RUN_FILE" >&2
  exit 1
fi

python3 - "$RUN_FILE" <<'PY'
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])

try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: invalid JSON: {exc}", file=sys.stderr)
    sys.exit(1)

errors = []
warnings = []

def require(obj, key, ctx):
    if key not in obj or obj[key] in (None, "", []):
        errors.append(f"{ctx} missing {key}")
        return None
    return obj[key]

for key in ["run_id", "run_time", "sector_state_ref", "recommendations", "evidence"]:
    require(data, key, "run")

pool_audit = data.get("candidate_pool_audit") or {}
if pool_audit:
    for warning in pool_audit.get("warnings") or []:
        warnings.append(f"candidate_pool_audit: {warning}")

selection_policy = data.get("selection_policy") or {}
if selection_policy.get("style") == "short_term_mainline":
    selected_mainlines = selection_policy.get("selected_mainlines") or []
    if not selected_mainlines:
        errors.append("selection_policy short_term_mainline requires selected_mainlines")
    if pool_audit.get("missing_mainlines"):
        warnings.append(
            "candidate_pool_audit: selected short-term mainlines missing from stock pool"
        )

recommendations = data.get("recommendations") or []
evidence = data.get("evidence") or []
discovery_seen = 0

if not isinstance(recommendations, list):
    errors.append("run recommendations must be an array")
    recommendations = []

if not isinstance(evidence, list):
    errors.append("run evidence must be an array")
    evidence = []

evidence_by_id = {}
for idx, item in enumerate(evidence):
    ctx = f"evidence[{idx}]"
    if not isinstance(item, dict):
        errors.append(f"{ctx} must be an object")
        continue
    evidence_id = require(item, "id", ctx)
    if evidence_id:
        evidence_by_id[evidence_id] = item
    for key in ["source_name", "data_time", "raw_value", "normalized_value", "unit"]:
        require(item, key, ctx)

run_time = str(data.get("run_time", ""))
is_0900 = bool(re.search(r"T09:0\d| 09:0\d|09:00", run_time)) or data.get("task_type") == "daily_0900_recommendation"

for idx, rec in enumerate(recommendations):
    ctx = f"recommendations[{idx}]"
    if not isinstance(rec, dict):
        errors.append(f"{ctx} must be an object")
        continue

    for key in ["name", "code", "exchange", "sector", "sector_status", "attention_level", "price_reference", "evidence_ids", "participation_role", "execution_risk"]:
        require(rec, key, ctx)

    evidence_ids = rec.get("evidence_ids") or []
    if not isinstance(evidence_ids, list):
        errors.append(f"{ctx} evidence_ids must be an array")
        evidence_ids = []
    if len(evidence_ids) < 2:
        errors.append(f"{ctx} must have at least 2 evidence_ids")
    for evidence_id in evidence_ids:
        if evidence_id not in evidence_by_id:
            errors.append(f"{ctx} references missing evidence id {evidence_id}")

    sector_status = rec.get("sector_status")
    attention_level = rec.get("attention_level")
    participation_role = rec.get("participation_role")
    execution_risk = rec.get("execution_risk")
    if participation_role != "recommendation":
        errors.append(f"{ctx} recommendations must have participation_role=recommendation")
    if execution_risk == "high":
        errors.append(f"{ctx} high execution_risk cannot enter recommendations")
    signals = rec.get("trading_signals") or {}
    if isinstance(signals, dict):
        if signals.get("opening_limit_up") or signals.get("quick_limit_up"):
            errors.append(f"{ctx} opening/quick limit-up names must be sector_anchors, not recommendations")
        try:
            if float(signals.get("limit_up_count_5d") or 0) >= 2:
                errors.append(f"{ctx} repeated recent limit-up names must be sector_anchors, not recommendations")
        except (TypeError, ValueError):
            pass
        try:
            if float(signals.get("short_term_gain_pct") or 0) >= 35:
                errors.append(f"{ctx} excessive short-term gain names must be sector_anchors, not recommendations")
        except (TypeError, ValueError):
            pass
    if sector_status == "low_activity" and attention_level == "high":
        errors.append(f"{ctx} low_activity sector cannot have high attention")

    if selection_policy.get("style") == "short_term_mainline":
        short_term_fit = rec.get("short_term_fit")
        if not isinstance(short_term_fit, dict) or not short_term_fit:
            errors.append(f"{ctx} short_term_mainline requires short_term_fit")
        else:
            for key in ["mainline", "fundamental_score", "capital_score", "short_term_gain_pct"]:
                if key not in short_term_fit or short_term_fit[key] in (None, ""):
                    errors.append(f"{ctx}.short_term_fit missing {key}")
            bucket = short_term_fit.get("selection_bucket")
            if bucket not in {"mainline", "evidence_backed_discovery"}:
                errors.append(f"{ctx}.short_term_fit invalid selection_bucket")
            if bucket == "evidence_backed_discovery":
                discovery_seen += 1

    overheat_risk = rec.get("overheat_risk")
    if overheat_risk == "high" and attention_level == "high" and not rec.get("fresh_catalyst_evidence_id"):
        errors.append(f"{ctx} high overheat_risk requires fresh_catalyst_evidence_id for high attention")

    price = rec.get("price_reference")
    if not isinstance(price, dict):
        errors.append(f"{ctx} price_reference must be an object")
    else:
        for key in ["price_type", "data_time", "source", "evidence_id"]:
            require(price, key, f"{ctx}.price_reference")
        price_type = price.get("price_type")
        if is_0900 and price_type == "intraday_realtime":
            errors.append(f"{ctx} 09:00 run cannot use intraday_realtime price")
        if price_type == "predicted" and not price.get("is_prediction", False):
            errors.append(f"{ctx} predicted price must set is_prediction=true")
        evidence_id = price.get("evidence_id")
        if evidence_id and evidence_id not in evidence_by_id:
            errors.append(f"{ctx}.price_reference references missing evidence id {evidence_id}")

    for item_idx, item in enumerate(rec.get("key_data") or []):
        if not isinstance(item, dict):
            errors.append(f"{ctx}.key_data[{item_idx}] must be an object")
            continue
        if item.get("evidence_id") and item["evidence_id"] not in evidence_by_id:
            errors.append(f"{ctx}.key_data[{item_idx}] references missing evidence id {item['evidence_id']}")

if selection_policy.get("style") == "short_term_mainline":
    try:
        discovery_limit = int(selection_policy.get("discovery_count", 1))
    except (TypeError, ValueError):
        discovery_limit = 1
    if discovery_seen > discovery_limit:
        errors.append(
            f"short_term_mainline discovery recommendations exceed discovery_count: {discovery_seen}>{discovery_limit}"
        )

text = json.dumps(data, ensure_ascii=False)
for pattern in [
    r"无条件买入",
    r"建议买入",
    r"建议卖出",
    r"建议加仓",
    r"建议满仓",
    r"满仓",
    r"梭哈",
    r"稳赚",
    r"必涨",
    r"收益承诺",
    r"建议仓位",
]:
    if re.search(pattern, text):
        errors.append(f"forbidden expression matched: {pattern}")

if errors:
    print("Run validation failed:")
    for error in errors:
        print(f"- {error}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    sys.exit(1)

print("Run validation passed")
print(f"Recommendations: {len(recommendations)}")
print(f"Evidence: {len(evidence_by_id)}")
if warnings:
    print("Warnings:")
    for warning in warnings:
        print(f"- {warning}")
PY
