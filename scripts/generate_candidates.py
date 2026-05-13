#!/usr/bin/env python3
"""Generate structured recommendation candidates from stocks and sector state."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sector_map(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("name"): item for item in state.get("sectors", []) if item.get("name")}


def row_score(row: dict[str, str], sector: dict[str, Any]) -> float:
    score = 0.0
    if sector.get("status") == "hot":
        score += 35
    elif sector.get("status") == "improving":
        score += 30
    elif sector.get("status") == "contrarian":
        score += 10
    elif sector.get("status") == "low_activity":
        score -= 20
    if row.get("catalyst"):
        score += 25
    try:
        score += min(max(float(row.get("fundamental_score", "0")), 0), 20)
    except ValueError:
        pass
    try:
        score += min(max(float(row.get("capital_score", "0")), -10), 15)
    except ValueError:
        pass
    if sector.get("overheat_risk") == "high":
        score -= 20
    return score


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate structured candidates")
    parser.add_argument("--stocks-csv", required=True, help="CSV stock pool")
    parser.add_argument("--sector-state", default="runtime/sector-state.latest.json")
    parser.add_argument("--output", "-o", default="runtime/candidates.latest.json")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    sectors = sector_map(load_json(args.sector_state))
    rows = []
    with Path(args.stocks_csv).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            sector = sectors.get(row.get("sector"), {})
            score = row_score(row, sector)
            if sector.get("status") == "low_activity" and row.get("force_include") != "true":
                continue
            rows.append((score, row, sector))
    rows.sort(key=lambda item: item[0], reverse=True)

    evidence = []
    recommendations = []
    for idx, (score, row, sector) in enumerate(rows[: args.limit], start=1):
        price_eid = f"E{idx}P"
        sector_eid = f"E{idx}S"
        evidence.extend(
            [
                {
                    "id": price_eid,
                    "source_name": row.get("price_source", "manual"),
                    "source_type": "market_data",
                    "stability_tier": row.get("price_stability_tier", "S3"),
                    "url": row.get("price_url", "https://example.com"),
                    "data_time": row.get("price_data_time"),
                    "raw_value": row.get("price_raw_value"),
                    "normalized_value": float(row.get("previous_close", "0")),
                    "unit": "元",
                    "transform": row.get("price_transform", "无"),
                    "supports": ["price_reference.previous_close"],
                },
                {
                    "id": sector_eid,
                    "source_name": "sector-state",
                    "source_type": "sector_state",
                    "stability_tier": "runtime",
                    "url": args.sector_state,
                    "data_time": sector.get("last_updated") or "",
                    "raw_value": sector.get("status"),
                    "normalized_value": sector.get("status"),
                    "unit": "status",
                    "transform": "无",
                    "supports": ["sector_status"],
                },
            ]
        )
        recommendations.append(
            {
                "name": row.get("name"),
                "code": row.get("code"),
                "exchange": row.get("exchange"),
                "sector": row.get("sector"),
                "attention_level": row.get("attention_level") or ("high" if score >= 60 else "medium"),
                "recommendation_type": row.get("recommendation_type", "policy_catalyst"),
                "fresh_catalyst_evidence_id": row.get("fresh_catalyst_evidence_id") or None,
                "recommendation_reason": [row.get("catalyst") or "板块状态和基础评分入选"],
                "key_data": [],
                "price_reference": {
                    "price_type": "previous_close",
                    "value": float(row.get("previous_close", "0")),
                    "unit": "元",
                    "data_time": row.get("price_data_time"),
                    "source": row.get("price_source", "manual"),
                    "evidence_id": price_eid,
                },
                "risks": [row.get("risk", "需持续跟踪板块热度和个股基本面")],
                "invalid_if": [row.get("invalid_if", "板块催化证伪或相对强度走弱")],
                "evidence_ids": [price_eid, sector_eid],
            }
        )

    payload = {
        "run_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "run_time": datetime.now().astimezone().isoformat(),
        "recommendations": recommendations,
        "evidence": evidence,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Candidates: {len(recommendations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
