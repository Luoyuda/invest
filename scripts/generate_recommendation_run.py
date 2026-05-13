#!/usr/bin/env python3
"""Generate recommendation-runs/latest.json from structured candidates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sector_map(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("name"): item for item in state.get("sectors", []) if item.get("name")}


def normalize_candidate(candidate: dict[str, Any], sectors: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sector_name = candidate.get("sector")
    sector = sectors.get(sector_name, {})
    evidence_ids = candidate.get("evidence_ids") or []
    price = candidate.get("price_reference") or {}
    if price.get("evidence_id") and price["evidence_id"] not in evidence_ids:
        evidence_ids.append(price["evidence_id"])
    for item in candidate.get("key_data") or []:
        if item.get("evidence_id") and item["evidence_id"] not in evidence_ids:
            evidence_ids.append(item["evidence_id"])

    return {
        "name": candidate.get("name"),
        "code": candidate.get("code"),
        "exchange": candidate.get("exchange"),
        "sector": sector_name,
        "sector_status": candidate.get("sector_status") or sector.get("status", "unknown"),
        "recommendation_type": candidate.get("recommendation_type", "policy_catalyst"),
        "attention_level": candidate.get("attention_level", "medium"),
        "overheat_risk": candidate.get("overheat_risk") or sector.get("overheat_risk", "low"),
        "fresh_catalyst_evidence_id": candidate.get("fresh_catalyst_evidence_id"),
        "participation_role": candidate.get("participation_role", "recommendation"),
        "execution_risk": candidate.get("execution_risk", "unknown"),
        "trading_signals": candidate.get("trading_signals", {}),
        "exclusion_reason": candidate.get("exclusion_reason", []),
        "recommendation_reason": candidate.get("recommendation_reason", []),
        "key_data": candidate.get("key_data", []),
        "price_reference": price,
        "risks": candidate.get("risks", []),
        "invalid_if": candidate.get("invalid_if", []),
        "evidence_ids": evidence_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate recommendation run JSON")
    parser.add_argument("--candidates", "-c", required=True, help="JSON with recommendations[]/evidence[]")
    parser.add_argument("--sector-state", "-s", default="runtime/sector-state.latest.json")
    parser.add_argument("--output", "-o", default="runtime/recommendation-runs/latest.json")
    parser.add_argument("--task-type", default="daily_0900_recommendation")
    args = parser.parse_args()

    candidates_payload = load_json(args.candidates)
    sector_state = load_json(args.sector_state)
    sectors = sector_map(sector_state)
    now = datetime.now().astimezone()

    recommendations_input = candidates_payload.get("recommendations", [])
    sector_anchors_input = candidates_payload.get("sector_anchors", [])
    evidence = candidates_payload.get("evidence", [])
    recommendations = [normalize_candidate(item, sectors) for item in recommendations_input]
    sector_anchors = [normalize_candidate(item, sectors) for item in sector_anchors_input]

    payload = {
        "run_id": candidates_payload.get("run_id") or now.strftime("%Y%m%d-%H%M%S"),
        "run_time": candidates_payload.get("run_time") or now.isoformat(),
        "task_type": args.task_type,
        "sector_state_ref": {
            "path": args.sector_state,
            "as_of": sector_state.get("as_of"),
            "valid_until": sector_state.get("valid_until"),
            "status": "valid",
        },
        "price_time_policy": candidates_payload.get(
            "price_time_policy",
            {
                "run_session": "pre_open",
                "allowed_price_types": ["previous_close", "latest_verifiable"],
                "disallow": ["intraday_realtime"],
            },
        ),
        "recommendations": recommendations,
        "sector_anchors": sector_anchors,
        "evidence": evidence,
        "validation": {"status": "pending", "checked_at": None, "errors": [], "warnings": []},
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Recommendations: {len(recommendations)}")
    print(f"Evidence: {len(evidence)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
