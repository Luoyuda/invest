#!/usr/bin/env python3
"""Fetch A-share capital-flow data from licensed iFinD data only.

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


def fetch_stock_flow(code: str, days: int, timeout: float, config: str | None) -> dict[str, Any]:
    query = f"{code} A股 最近{days}个交易日 主力资金流向 大单 中单 小单 净流入 净流出"
    result = call_ifind("hexin-ifind-stock.get_stock_perfomance", query, timeout=timeout, config=config)
    return {
        "code": code,
        "provider": "ifind",
        "status": "passed",
        "data_time": None,
        "window_days": days,
        "latest": None,
        "recent": {},
        "summary": {
            "today_main_net_inflow_yi": None,
            "today_bias": "unknown",
            "recent_20d_main_net_inflow_yi": None,
            "recent_5d_main_net_inflow_yi": None,
            "interpretation_boundary": "资金流优先来自 iFinD skill；本 CLI 使用授权 iFinD MCP 兜底查询。字段以 raw_response 为准，不从未授权网页接口补数。",
        },
        "history": [],
        "source": result["source"],
        "raw_response": result["data"],
        "raw_stdout": result["stdout"],
        "provider_results": [{"provider": "ifind", "status": "passed", "tool": result["tool"], "query": result["query"]}],
    }


def fetch_market_flow(limit: int, timeout: float, config: str | None) -> dict[str, Any]:
    query = f"A股市场 行业 概念 主力资金流向 净流入 净流出 排名前{limit}"
    result = call_ifind("hexin-ifind-stock.search_stocks", query, timeout=timeout, config=config)
    return {
        "provider": "ifind",
        "scope": "market",
        "status": "passed",
        "data_time": None,
        "is_market_total": False,
        "scope_note": "大盘资金方向来自 iFinD MCP 自然语言查询结果；未取得明确全市场总额时不得写成精确总流入/总流出。",
        "summary": {
            "strong_industries": [],
            "weak_industries": [],
            "strong_concepts": [],
            "weak_concepts": [],
            "interpretation_boundary": "只使用 iFinD MCP 返回内容，不通过网页 JS_DATA 或公开页补齐。",
        },
        "source": result["source"],
        "raw_response": result["data"],
        "raw_stdout": result["stdout"],
        "provider_results": [{"provider": "ifind", "status": "passed", "tool": result["tool"], "query": result["query"]}],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch A-share capital-flow data through iFinD MCP")
    parser.add_argument("codes", nargs="*", help="A-share stock codes, e.g. 300308 600519")
    parser.add_argument("--scope", choices=["stock", "market"], default="stock")
    parser.add_argument("--provider", choices=["ifind"], default="ifind")
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--limit", type=int, default=50, help="Market ranking rows to request when --scope market")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--config", default=None)
    parser.add_argument("--output", "-o", default="runtime/capital-flow.latest.json")
    parser.add_argument("--require-results", action="store_true")
    args = parser.parse_args()

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    if args.scope == "market":
        try:
            results.append(fetch_market_flow(args.limit, args.timeout, args.config))
        except Exception as exc:  # noqa: BLE001 - command-line diagnostics
            errors.append({"scope": "market", "provider": "ifind", "error": str(exc)})
    else:
        if not args.codes:
            raise SystemExit("stock scope requires at least one code")
        for code in args.codes:
            try:
                results.append(fetch_stock_flow(code, args.days, args.timeout, args.config))
            except Exception as exc:  # noqa: BLE001 - command-line diagnostics
                errors.append({"code": code, "provider": "ifind", "error": str(exc)})

    status = "passed" if results and not errors else "degraded" if results else "failed"
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "scope": args.scope,
        "provider": "ifind",
        "status": status,
        "results": results,
        "errors": errors,
        "warnings": [] if results else ["no iFinD capital flow data available"],
        "source_policy": "Licensed iFinD data only: use iFinD skill first when available, otherwise iFinD MCP for automation/gaps. No Eastmoney/THS public webpage fallback is permitted.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Status: {status}")
    print(f"Results: {len(results)}")
    if errors:
        print(f"Errors: {len(errors)}", file=sys.stderr)
    if args.require_results and not results:
        return 2
    return 0 if results else 2


if __name__ == "__main__":
    raise SystemExit(main())
