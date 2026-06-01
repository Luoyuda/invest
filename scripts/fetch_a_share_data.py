#!/usr/bin/env python3
"""Fetch A-share quote summaries from licensed iFinD data only.

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


def fetch_quote(code: str, timeout: float, config: str | None) -> dict[str, Any]:
    query = f"{code} A股 股票信息摘要 最新行情 最新价 涨跌幅 成交额 昨收 数据时间"
    result = call_ifind("hexin-ifind-stock.get_stock_summary", query, timeout=timeout, config=config)
    return {
        "code": code,
        "name": None,
        "exchange": None,
        "latest_price": None,
        "previous_close": None,
        "open": None,
        "high": None,
        "low": None,
        "volume": None,
        "turnover": None,
        "change": None,
        "pct_change": None,
        "data_time": None,
        "provider": "ifind",
        "source": result["source"],
        "raw_response": result["data"],
        "raw_stdout": result["stdout"],
        "provider_results": [{"provider": "ifind", "status": "ok", "tool": result["tool"], "query": result["query"]}],
        "quality": {"status": "licensed_source", "warnings": [], "checks": []},
        "source_policy": "iFinD skill first for interactive use; this CLI uses iFinD MCP fallback. No unlicensed web fallback is permitted.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch A-share quotes through iFinD MCP")
    parser.add_argument("codes", nargs="+", help="A-share stock codes, e.g. 000001 600000")
    parser.add_argument("--output", "-o", default="runtime/market-data/latest-quotes.json")
    parser.add_argument("--provider", choices=["ifind"], default="ifind")
    parser.add_argument("--providers", default="ifind", help="Compatibility alias; only ifind is allowed")
    parser.add_argument("--config", default=None, help="mcporter config path; defaults to IFIND_MCP_CONFIG or ~/.openclaw/mcporter.json")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-price-diff-pct", type=float, default=0.5, help="Kept for CLI compatibility; unused with single licensed source")
    args = parser.parse_args()
    providers = [item.strip().lower() for item in args.providers.split(",") if item.strip()]
    if providers != ["ifind"]:
        raise SystemExit("only provider 'ifind' is allowed")

    quotes: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for code in args.codes:
        try:
            quotes.append(fetch_quote(code, args.timeout, args.config))
        except Exception as exc:  # noqa: BLE001 - command-line diagnostics
            errors.append({"code": code, "provider": "ifind", "error": str(exc)})

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_policy": "Licensed iFinD data only: use iFinD skill first when available, otherwise iFinD MCP for automation/gaps. Do not fall back to Sina/Tencent/Eastmoney/adata or other unguaranteed sources.",
        "providers": ["ifind"],
        "quotes": quotes,
        "errors": errors,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Quotes: {len(quotes)}")
    if errors:
        print(f"Errors: {len(errors)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
