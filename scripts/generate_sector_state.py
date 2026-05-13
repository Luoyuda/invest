#!/usr/bin/env python3
"""Generate runtime/sector-state.latest.json from sector metrics.

Input is intentionally simple JSON so daily/weekly jobs can feed this script
from AKShare, Eastmoney exports, CSV conversions, or manual research.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def num(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def classify(item: dict[str, Any]) -> tuple[str, str, list[str], str]:
    rs_5d = num(item.get("relative_strength_5d"))
    turnover = num(item.get("turnover_change_5d"))
    breadth = num(item.get("breadth"))
    catalyst = bool(item.get("policy_industry_catalyst"))
    capital = num(item.get("capital_flow_score"))
    overheat = num(item.get("overheat_score"))

    positives = sum([rs_5d > 0, turnover > 0, breadth >= 0.55, catalyst, capital > 0])
    negatives = sum([rs_5d < 0, turnover < 0, breadth < 0.45, not catalyst, capital < 0])

    crowding = []
    if overheat >= 0.75:
        crowding.append("overheat_score_high")
    if breadth < 0.45 and rs_5d > 0:
        crowding.append("narrow_leadership")

    if positives >= 3:
        status = "hot"
    elif catalyst and positives >= 2:
        status = "improving"
    elif negatives >= 3:
        status = "low_activity"
    elif item.get("contrarian_reason"):
        status = "contrarian"
    else:
        status = "unknown"

    confidence = "high" if abs(positives - negatives) >= 3 else "medium"
    if status == "unknown":
        confidence = "low"

    overheat_risk = "high" if overheat >= 0.75 else "medium" if overheat >= 0.45 else "low"
    return status, confidence, crowding, overheat_risk


def build_sector(item: dict[str, Any]) -> dict[str, Any]:
    status, confidence, crowding_signals, overheat_risk = classify(item)
    source_refs = item.get("source_refs") or []
    return {
        "name": item["name"],
        "status": status,
        "confidence": confidence,
        "evidence_window": item.get("evidence_window", "5d"),
        "policy_industry_catalyst": item.get("policy_industry_catalyst"),
        "relative_strength": item.get("relative_strength", item.get("relative_strength_5d")),
        "turnover_heat": item.get("turnover_heat", item.get("turnover_change_5d")),
        "breadth": item.get("breadth"),
        "capital_flow": item.get("capital_flow", item.get("capital_flow_score")),
        "overheat_risk": overheat_risk,
        "crowding_signals": crowding_signals,
        "upgrade_triggers": item.get("upgrade_triggers", []),
        "downgrade_triggers": item.get("downgrade_triggers", []),
        "source_refs": source_refs,
        "status_reason": item.get("status_reason") or f"positives/negatives classified from 5d metrics; status={status}",
        "last_updated": item.get("data_time") or datetime.now().astimezone().isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sector-state.latest.json")
    parser.add_argument("--input", "-i", required=True, help="JSON file with sectors[] metrics")
    parser.add_argument("--output", "-o", default="runtime/sector-state.latest.json")
    parser.add_argument("--valid-days", type=int, default=5)
    parser.add_argument("--benchmark", default="沪深300")
    parser.add_argument("--generated-by", default="weekly_refresh")
    args = parser.parse_args()

    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    sectors_input = source.get("sectors", source if isinstance(source, list) else [])
    if not isinstance(sectors_input, list):
        raise SystemExit("input must be a list or an object with sectors[]")

    now = datetime.now().astimezone()
    as_of = source.get("as_of") or now.date().isoformat()
    valid_until = source.get("valid_until") or (now + timedelta(days=args.valid_days)).date().isoformat()
    sectors = [build_sector(item) for item in sectors_input if item.get("name")]

    payload = {
        "as_of": as_of,
        "valid_until": valid_until,
        "generated_at": now.isoformat(),
        "generated_by": args.generated_by,
        "benchmark": source.get("benchmark") or args.benchmark,
        "sectors": sectors,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Sectors: {len(sectors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
