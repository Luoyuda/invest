#!/usr/bin/env python3
"""Generate structured recommendation candidates from stocks and sector state."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ANCHOR_REASONS = {
    "opening_limit_up": "开盘即涨停或一字板，普通投资者可参与性差",
    "quick_limit_up": "开盘后快速封板，成交窗口短且容易高位站岗",
    "limit_up_count_5d": "近 5 个交易日多次涨停，短线筹码拥挤",
    "short_term_gain_pct": "近 10 个交易日涨幅过大，追高风险高",
}


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sector_map(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("name"): item for item in state.get("sectors", []) if item.get("name")}


def preferred_sectors(state: dict[str, Any]) -> list[str]:
    return [item["name"] for item in rank_mainlines(state, limit=6) if item.get("name")]


def metric_num(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def sector_short_term_score(sector: dict[str, Any]) -> float:
    """Score sectors for the user's short-term style.

    Short-term recommendation starts from the fastest, most funded mainlines,
    then looks for still-participable stocks inside those directions.
    """

    status = sector.get("status")
    score = 0.0
    if status == "hot":
        score += 35
    elif status == "improving":
        score += 25
    elif status == "contrarian":
        score += 5
    elif status == "low_activity":
        score -= 50
    score += min(max(metric_num(sector.get("relative_strength")), -10), 20) * 1.4
    score += min(max(metric_num(sector.get("capital_flow")), -20), 20) * 1.2
    score += min(max(metric_num(sector.get("turnover_heat")), -20), 20) * 0.6
    score += min(max(metric_num(sector.get("breadth")) * 10, 0), 10)
    if sector.get("policy_industry_catalyst"):
        score += 12
    if sector.get("overheat_risk") == "high":
        score -= 12
    return score


def rank_mainlines(state: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    sectors = [item for item in state.get("sectors", []) if item.get("name")]
    viable = [item for item in sectors if item.get("status") in {"hot", "improving"}]
    ranked = sorted(viable, key=sector_short_term_score, reverse=True)
    return ranked[:limit]


def parse_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "是"}


def parse_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return default


def parse_int(value: str | None, default: int = 0) -> int:
    try:
        return int(float(str(value or "").strip()))
    except ValueError:
        return default


def tradability_flags(row: dict[str, str]) -> dict[str, Any]:
    """Classify execution risk for ordinary investors.

    Strong limit-up names can still identify the main sector, but they should not
    be treated as front-list recommendations when realistic participation is poor.
    """

    limit_up_count_5d = parse_int(row.get("limit_up_count_5d"))
    short_term_gain_pct = parse_float(row.get("short_term_gain_pct"))
    flags = {
        "opening_limit_up": parse_bool(row.get("opening_limit_up")),
        "quick_limit_up": parse_bool(row.get("quick_limit_up")),
        "limit_up_count_5d": limit_up_count_5d,
        "short_term_gain_pct": short_term_gain_pct,
    }
    reasons: list[str] = []
    if flags["opening_limit_up"]:
        reasons.append(ANCHOR_REASONS["opening_limit_up"])
    if flags["quick_limit_up"]:
        reasons.append(ANCHOR_REASONS["quick_limit_up"])
    if limit_up_count_5d >= 2:
        reasons.append(ANCHOR_REASONS["limit_up_count_5d"])
    if short_term_gain_pct >= 35:
        reasons.append(ANCHOR_REASONS["short_term_gain_pct"])

    if reasons:
        role = "sector_anchor"
        risk = "high"
    elif limit_up_count_5d == 1 or short_term_gain_pct >= 20:
        role = "recommendation"
        risk = "medium"
    else:
        role = "recommendation"
        risk = "low"
    return {"participation_role": role, "execution_risk": risk, "reasons": reasons, "flags": flags}


def row_score(row: dict[str, str], sector: dict[str, Any], mainline_names: set[str]) -> float:
    score = 0.0
    if sector.get("status") == "hot":
        score += 25
    elif sector.get("status") == "improving":
        score += 20
    elif sector.get("status") == "contrarian":
        score += 10
    elif sector.get("status") == "low_activity":
        score -= 20
    if row.get("sector") in mainline_names:
        score += 25
    else:
        score -= 15
    score += min(max(metric_num(sector.get("relative_strength")), -10), 20) * 0.8
    score += min(max(metric_num(sector.get("capital_flow")), -20), 20) * 0.8
    if row.get("catalyst"):
        score += 15
    score += min(max(parse_float(row.get("fundamental_score")), 0), 20)
    score += min(max(parse_float(row.get("capital_score")), -10), 15)
    gain = parse_float(row.get("short_term_gain_pct"))
    if gain <= 8:
        score += 10
    elif gain <= 15:
        score += 6
    elif gain <= 25:
        score -= 4
    elif gain < 35:
        score -= 10
    if sector.get("overheat_risk") == "high":
        score -= 20
    return score


def is_discovery_candidate(row: dict[str, str], sector: dict[str, Any], mainline_names: set[str]) -> bool:
    """Allow a small number of evidence-backed non-mainline ideas.

    The recommendation style should not become a narrow "only current top 3
    sectors" filter, but non-mainline names need objective evidence rather than
    just low valuation or familiarity.
    """

    if row.get("sector") in mainline_names:
        return False
    if parse_bool(row.get("force_include")):
        return True
    if sector.get("status") == "low_activity":
        return False
    if sector.get("status") not in {"hot", "improving", "contrarian"}:
        return False
    has_catalyst = bool(row.get("catalyst") or sector.get("policy_industry_catalyst"))
    capital_or_heat = (
        parse_float(row.get("capital_score")) > 0
        or metric_num(sector.get("capital_flow")) > 0
        or metric_num(sector.get("turnover_heat")) > 0
    )
    strength_or_improving = metric_num(sector.get("relative_strength")) > 0 or sector.get("status") == "improving"
    not_overextended = parse_float(row.get("short_term_gain_pct")) < 25
    return has_catalyst and capital_or_heat and strength_or_improving and not_overextended


def build_pool_audit(
    rows: list[tuple[float, dict[str, str], dict[str, Any]]],
    sectors: dict[str, dict[str, Any]],
    mainlines: list[dict[str, Any]],
) -> dict[str, Any]:
    sector_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for _, row, _ in rows:
        sector_name = row.get("sector") or "unknown"
        sector_counts[sector_name] = sector_counts.get(sector_name, 0) + 1
        source = row.get("candidate_source") or row.get("price_source") or "manual"
        source_counts[source] = source_counts.get(source, 0) + 1
    preferred = preferred_sectors({"sectors": list(sectors.values())})
    missing_preferred = [name for name in preferred if name not in sector_counts]
    selected_mainlines = [item.get("name") for item in mainlines if item.get("name")]
    missing_mainlines = [name for name in selected_mainlines if name not in sector_counts]
    warnings = []
    if missing_preferred:
        warnings.append("preferred sectors missing from stock pool; recommendation may have availability bias")
    if missing_mainlines:
        warnings.append("selected short-term mainlines missing from stock pool; recommendation may miss active opportunities")
    if len(sector_counts) < 3:
        warnings.append("stock pool covers fewer than 3 sectors; diversify upstream candidate collection")
    return {
        "pool_size": len(rows),
        "sector_counts": sector_counts,
        "candidate_source_counts": source_counts,
        "preferred_sectors": preferred,
        "selected_mainlines": selected_mainlines,
        "missing_mainlines": missing_mainlines,
        "missing_preferred_sectors": missing_preferred,
        "warnings": warnings,
    }


def build_item(
    row: dict[str, str],
    sector: dict[str, Any],
    price_eid: str,
    sector_eid: str,
    tradability: dict[str, Any],
    score: float,
    mainline_names: set[str],
) -> dict[str, Any]:
    attention = row.get("attention_level") or ("high" if score >= 60 else "medium")
    if tradability["execution_risk"] == "medium" and attention == "high":
        attention = "medium"
    return {
        "name": row.get("name"),
        "code": row.get("code"),
        "exchange": row.get("exchange"),
        "sector": row.get("sector"),
        "sector_status": sector.get("status", "unknown"),
        "overheat_risk": sector.get("overheat_risk", "low"),
        "attention_level": attention,
        "recommendation_type": row.get("recommendation_type", "policy_catalyst"),
        "short_term_fit": {
            "mainline": row.get("sector"),
            "selection_bucket": "mainline" if row.get("sector") in mainline_names else "evidence_backed_discovery",
            "fundamental_score": parse_float(row.get("fundamental_score")),
            "capital_score": parse_float(row.get("capital_score")),
            "short_term_gain_pct": parse_float(row.get("short_term_gain_pct")),
            "style": "mainline_first_with_evidence_backed_discovery",
        },
        "fresh_catalyst_evidence_id": row.get("fresh_catalyst_evidence_id") or None,
        "participation_role": tradability["participation_role"],
        "execution_risk": tradability["execution_risk"],
        "trading_signals": tradability["flags"],
        "exclusion_reason": tradability["reasons"],
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate structured candidates")
    parser.add_argument("--stocks-csv", required=True, help="CSV stock pool")
    parser.add_argument("--sector-state", default="runtime/sector-state.latest.json")
    parser.add_argument("--output", "-o", default="runtime/candidates.latest.json")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--mainline-count", type=int, default=3)
    parser.add_argument("--discovery-count", type=int, default=1)
    parser.add_argument("--max-per-sector", type=int, default=2)
    args = parser.parse_args()

    sector_state = load_json(args.sector_state)
    sectors = sector_map(sector_state)
    mainlines = rank_mainlines(sector_state, limit=args.mainline_count)
    mainline_names = {item["name"] for item in mainlines if item.get("name")}
    rows = []
    with Path(args.stocks_csv).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            sector = sectors.get(row.get("sector"), {})
            score = row_score(row, sector, mainline_names)
            if sector.get("status") == "low_activity" and not parse_bool(row.get("force_include")):
                continue
            rows.append((score, row, sector))
    rows.sort(key=lambda item: item[0], reverse=True)

    evidence = []
    recommendations = []
    sector_anchors = []
    selected_count = 0
    selected_discovery_count = 0
    selected_sector_counts: dict[str, int] = {}
    for idx, (score, row, sector) in enumerate(rows, start=1):
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
        tradability = tradability_flags(row)
        item = build_item(row, sector, price_eid, sector_eid, tradability, score, mainline_names)
        if tradability["participation_role"] == "sector_anchor":
            sector_anchors.append(item)
            continue
        if selected_count >= args.limit:
            continue
        sector_name = row.get("sector") or "unknown"
        in_mainline = sector_name in mainline_names
        is_discovery = not in_mainline
        if is_discovery:
            if not is_discovery_candidate(row, sector, mainline_names):
                continue
            if selected_discovery_count >= args.discovery_count:
                continue
        if selected_sector_counts.get(sector_name, 0) >= args.max_per_sector:
            continue
        recommendations.append(item)
        selected_sector_counts[sector_name] = selected_sector_counts.get(sector_name, 0) + 1
        if is_discovery:
            selected_discovery_count += 1
        selected_count += 1

    payload = {
        "run_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "run_time": datetime.now().astimezone().isoformat(),
        "recommendations": recommendations,
        "sector_anchors": sector_anchors,
        "candidate_pool_audit": build_pool_audit(rows, sectors, mainlines),
        "selection_policy": {
            "style": "short_term_mainline",
            "mainline_count": args.mainline_count,
            "discovery_count": args.discovery_count,
            "selected_mainlines": [item.get("name") for item in mainlines],
            "max_per_sector": args.max_per_sector,
            "reason": "prioritize 2-3 fast and funded mainlines while reserving a small evidence-backed discovery slot for overlooked improving opportunities",
        },
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
