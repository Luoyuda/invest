#!/usr/bin/env python3
"""Fetch A-share sector board snapshots from licensed iFinD data only.

Interactive agents should call the iFinD skill first. This CLI uses iFinD MCP as
the fallback path for automation and skill gaps.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from ifind_mcp import call_ifind


def fetch_ifind_boards(kind: str, limit: int, timeout: float, config: str | None) -> dict[str, Any]:
    kind_name = "行业" if kind == "industry" else "概念"
    query = f"A股{kind_name}板块 涨跌幅 成交额 主力资金 领涨股 排名前{limit}"
    result = call_ifind("hexin-ifind-stock.search_stocks", query, timeout=timeout, config=config)
    return {
        "provider": "ifind",
        "kind": kind,
        "status": "passed",
        "warnings": [],
        "source": result["source"],
        "boards": [
            {
                "board_code": None,
                "name": f"iFinD {kind_name}板块查询",
                "pct_change": None,
                "change": None,
                "turnover": None,
                "market_value": None,
                "main_net_inflow": None,
                "rise_count": None,
                "fall_count": None,
                "leading_stock": None,
                "leading_stock_pct_change": None,
                "raw_response": result["data"],
                "raw_stdout": result["stdout"],
            }
        ],
        "tool": result["tool"],
        "query": result["query"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch A-share sector board snapshots through iFinD MCP")
    parser.add_argument("--provider", choices=["ifind"], default="ifind")
    parser.add_argument("--kind", choices=["industry", "concept"], default="concept")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--config", default=None)
    parser.add_argument("--output", "-o", default="runtime/market-data/sector-boards.latest.json")
    parser.add_argument("--require-results", action="store_true", help="Exit non-zero when no board data is available")
    args = parser.parse_args()

    errors: list[dict[str, str]] = []
    try:
        payload = fetch_ifind_boards(args.kind, args.limit, args.timeout, args.config)
    except Exception as exc:  # noqa: BLE001 - command-line diagnostics
        errors.append({"provider": "ifind", "error": str(exc)})
        payload = {
            "provider": "ifind",
            "kind": args.kind,
            "status": "failed",
            "warnings": ["iFinD MCP sector board query failed"],
            "boards": [],
        }

    payload["generated_at"] = datetime.now().astimezone().isoformat()
    payload["errors"] = errors
    payload["source_policy"] = "Licensed iFinD data only: use iFinD skill first when available, otherwise iFinD MCP for automation/gaps. No Eastmoney/Sohu/AKShare/adata fallback is permitted."

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Status: {payload.get('status', 'unknown')}")
    print(f"Boards: {len(payload.get('boards') or [])}")
    if errors:
        print(f"Errors: {len(errors)}", file=sys.stderr)
    if args.require_results and not payload.get("boards"):
        return 2
    return 0 if payload.get("boards") else 2


if __name__ == "__main__":
    raise SystemExit(main())
