#!/usr/bin/env python3
"""Search A-share news through licensed iFinD data only.

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


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Search news through iFinD MCP")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--providers", default="ifind", help="Compatibility alias; only ifind is allowed")
    parser.add_argument("--provider", choices=["ifind"], default="ifind")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--overall-timeout", type=float, default=30.0, help="Kept for CLI compatibility")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--config", default=None)
    parser.add_argument("--output", "-o", default="runtime/search-results.latest.json")
    parser.add_argument("--require-results", action="store_true", help="Exit non-zero when iFinD returns no result")
    args = parser.parse_args()
    providers = [item.strip().lower() for item in args.providers.split(",") if item.strip()]
    if providers != ["ifind"]:
        raise SystemExit("only provider 'ifind' is allowed")

    provider_results: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    try:
        query = f"{args.query} A股 公告 新闻 资讯 最近 {args.max_results}条"
        result = call_ifind("hexin-ifind-news.get_company_news", query, timeout=min(args.timeout, args.overall_timeout), config=args.config)
        provider_results.append({"provider": "ifind", "status": "ok", "tool": result["tool"], "query": result["query"], "count": 1})
        results.append(
            {
                "title": args.query,
                "url": "https://mcp.51ifind.com/#/docs/skill-solution",
                "snippet": result["stdout"],
                "published_at": None,
                "provider": "ifind",
                "source": result["source"],
                "raw_response": result["data"],
            }
        )
    except Exception as exc:  # noqa: BLE001 - command-line diagnostics
        provider_results.append({"provider": "ifind", "status": "error", "error": str(exc)})
        errors.append({"provider": "ifind", "error": str(exc)})

    status = "passed" if results else "failed"
    payload = {
        "generated_at": now_iso(),
        "query": args.query,
        "providers": ["ifind"],
        "status": status,
        "results": results[: args.max_results],
        "provider_results": provider_results,
        "errors": errors,
        "policy": "News discovery must use iFinD skill first when available; this CLI uses iFinD MCP fallback. No RSS, homepage scraping, Tavily, or Google News fallback is permitted.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Status: {status}")
    print(f"Results: {len(payload['results'])}")
    if args.require_results and not results:
        return 2
    if errors:
        print(f"Errors: {len(errors)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
