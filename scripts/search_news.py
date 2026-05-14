#!/usr/bin/env python3
"""Search market news with timeout budgets and provider fallback.

The script records provider failures instead of blocking downstream workflows.
It uses free RSS feeds by default, and supports Brave/Tavily when API keys are
configured.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "lobster-invest/1.0", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str, params: dict[str, str], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": "lobster-invest/1.0", **headers},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_text(url: str, params: dict[str, str], timeout: float) -> str:
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={"Accept": "application/rss+xml, application/xml, text/xml", "User-Agent": "lobster-invest/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "ignore")


def search_google_news_rss(query: str, timeout: float, max_results: int) -> list[dict[str, Any]]:
    text = get_text(
        "https://news.google.com/rss/search",
        {"q": query, "hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans"},
        timeout,
    )
    root = ElementTree.fromstring(text)
    results = []
    for item in root.findall(".//item")[:max_results]:
        results.append(
            {
                "title": item.findtext("title"),
                "url": item.findtext("link"),
                "snippet": item.findtext("description"),
                "published_at": item.findtext("pubDate"),
                "provider": "google_news_rss",
            }
        )
    return results


def search_tavily(query: str, timeout: float, max_results: int) -> list[dict[str, Any]]:
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is not configured")
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": max_results,
    }
    data = post_json("https://api.tavily.com/search", payload, {}, timeout)
    results = []
    for item in data.get("results") or []:
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("content"),
                "published_at": item.get("published_date"),
                "provider": "tavily",
            }
        )
    return results


def search_brave(query: str, timeout: float, max_results: int) -> list[dict[str, Any]]:
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        raise RuntimeError("BRAVE_API_KEY is not configured")
    data = get_json(
        "https://api.search.brave.com/res/v1/web/search",
        {"q": query, "count": str(max_results), "search_lang": "zh-hans", "country": "CN"},
        {"X-Subscription-Token": api_key},
        timeout,
    )
    results = []
    for item in ((data.get("web") or {}).get("results") or []):
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("description"),
                "published_at": item.get("age"),
                "provider": "brave",
            }
        )
    return results


PROVIDERS = {
    "google_news_rss": search_google_news_rss,
    "brave": search_brave,
    "tavily": search_tavily,
}


def parse_providers(value: str) -> list[str]:
    providers = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = [item for item in providers if item not in PROVIDERS]
    if unknown:
        raise ValueError(f"unknown search provider(s): {', '.join(unknown)}")
    return providers


def main() -> int:
    parser = argparse.ArgumentParser(description="Search news with provider fallback")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--providers", default="google_news_rss,brave,tavily")
    parser.add_argument("--timeout", type=float, default=8.0, help="Per-provider timeout seconds")
    parser.add_argument("--overall-timeout", type=float, default=20.0, help="Overall search budget seconds")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--output", "-o", default="runtime/search-results.latest.json")
    parser.add_argument("--require-results", action="store_true", help="Exit non-zero when no provider returns results")
    args = parser.parse_args()

    providers = parse_providers(args.providers)
    started = time.monotonic()
    provider_results = []
    merged: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for provider in providers:
        elapsed = time.monotonic() - started
        remaining = args.overall_timeout - elapsed
        if remaining <= 0:
            provider_results.append({"provider": provider, "status": "skipped", "error": "overall timeout exceeded"})
            continue
        timeout = max(0.1, min(args.timeout, remaining))
        provider_started = time.monotonic()
        try:
            results = PROVIDERS[provider](args.query, timeout, args.max_results)
            duration_ms = round((time.monotonic() - provider_started) * 1000)
            provider_results.append({"provider": provider, "status": "ok", "duration_ms": duration_ms, "count": len(results)})
            for item in results:
                url = item.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                merged.append(item)
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
            duration_ms = round((time.monotonic() - provider_started) * 1000)
            provider_results.append({"provider": provider, "status": "error", "duration_ms": duration_ms, "error": str(exc)})

    status = "passed" if merged else "degraded"
    payload = {
        "generated_at": now_iso(),
        "query": args.query,
        "providers": providers,
        "status": status,
        "results": merged[: args.max_results],
        "provider_results": provider_results,
        "policy": "Search failures are non-fatal by default; downstream tasks must degrade confidence when status=degraded.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Status: {status}")
    print(f"Results: {len(payload['results'])}")
    if args.require_results and not merged:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
