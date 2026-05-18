#!/usr/bin/env python3
"""Fetch A-share capital-flow data with explicit source limitations."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


def secid_for(code: str) -> str:
    code = code.strip()
    if code.startswith(("6", "9")):
        return f"1.{code}"
    if code.startswith(("0", "2", "3", "4", "8")):
        return f"0.{code}"
    raise ValueError(f"cannot infer exchange for code: {code}")


def fetch_json(url: str, params: dict[str, str], timeout: int = 10, retries: int = 1, referer: str = "https://quote.eastmoney.com/") -> dict[str, Any]:
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) lobster-invest/1.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": referer,
            "Connection": "close",
        },
    )
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - diagnostics should keep provider failure
            last_exc = exc
            if attempt < retries:
                time.sleep(0.3 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def fetch_json_url(url: str, timeout: int = 8, retries: int = 1, referer: str = "https://stockpage.10jqka.com.cn/") -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) lobster-invest/1.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": referer,
            "Connection": "close",
        },
    )
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - diagnostics should keep provider failure
            last_exc = exc
            if attempt < retries:
                time.sleep(0.3 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def fetch_text_url(url: str, timeout: int = 8, retries: int = 1, referer: str = "https://data.10jqka.com.cn/") -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) lobster-invest/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": referer,
            "Connection": "close",
        },
    )
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                content_type = (response.headers.get("Content-Type") or "").lower()
                encoding = "gbk" if "gbk" in content_type or "gb2312" in content_type else "utf-8"
                return raw.decode(encoding, "ignore")
        except Exception as exc:  # noqa: BLE001 - diagnostics should keep provider failure
            last_exc = exc
            if attempt < retries:
                time.sleep(0.3 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def to_float(value: Any) -> float | None:
    if value in (None, "-", ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def yuan_to_yi(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value / 100_000_000, 4)


def wan_to_yi(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value / 10_000, 4)


def amount_to_yi(value: str) -> float | None:
    text = re.sub(r"\s+", "", value.strip())
    if not text or text == "--":
        return None
    multiplier = 1.0
    if text.endswith("亿"):
        multiplier = 1.0
        text = text[:-1]
    elif text.endswith("万"):
        multiplier = 1 / 10_000
        text = text[:-1]
    elif text.endswith("元"):
        multiplier = 1 / 100_000_000
        text = text[:-1]
    number = to_float(text)
    if number is None:
        return None
    return round(number * multiplier, 4)


def sum_recent(rows: list[dict[str, Any]], days: int, key: str) -> float | None:
    values = [to_float(row.get(key)) for row in rows[-days:]]
    numbers = [item for item in values if item is not None]
    if not numbers:
        return None
    return yuan_to_yi(sum(numbers))


def parse_kline(line: str) -> dict[str, Any]:
    parts = line.split(",")
    if len(parts) < 13:
        raise ValueError(f"incomplete capital flow kline: {line}")
    return {
        "date": parts[0],
        "main_net_inflow": to_float(parts[1]),
        "small_net_inflow": to_float(parts[2]),
        "medium_net_inflow": to_float(parts[3]),
        "large_net_inflow": to_float(parts[4]),
        "super_large_net_inflow": to_float(parts[5]),
        "main_net_inflow_pct": to_float(parts[6]),
        "small_net_inflow_pct": to_float(parts[7]),
        "medium_net_inflow_pct": to_float(parts[8]),
        "large_net_inflow_pct": to_float(parts[9]),
        "super_large_net_inflow_pct": to_float(parts[10]),
        "close": to_float(parts[11]),
        "pct_change": to_float(parts[12]),
    }


def normalize_day(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": row.get("date"),
        "main_net_inflow_yuan": row.get("main_net_inflow"),
        "main_net_inflow_yi": yuan_to_yi(row.get("main_net_inflow")),
        "main_net_inflow_pct": row.get("main_net_inflow_pct"),
        "breakdown_yi": {
            "super_large": yuan_to_yi(row.get("super_large_net_inflow")),
            "large": yuan_to_yi(row.get("large_net_inflow")),
            "medium": yuan_to_yi(row.get("medium_net_inflow")),
            "small": yuan_to_yi(row.get("small_net_inflow")),
        },
        "breakdown_pct": {
            "super_large": row.get("super_large_net_inflow_pct"),
            "large": row.get("large_net_inflow_pct"),
            "medium": row.get("medium_net_inflow_pct"),
            "small": row.get("small_net_inflow_pct"),
        },
        "close": row.get("close"),
        "pct_change": row.get("pct_change"),
    }


def flow_bias(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > 0:
        return "net_inflow"
    if value < 0:
        return "net_outflow"
    return "flat"


def fetch_eastmoney_stock_flow(code: str, days: int, timeout: int) -> dict[str, Any]:
    payload = fetch_json(
        "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get",
        {
            "lmt": str(days),
            "klt": "101",
            "secid": secid_for(code),
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
        },
        timeout=timeout,
    )
    data = payload.get("data") or {}
    klines = data.get("klines") or []
    rows = [parse_kline(line) for line in klines if line]
    if not rows:
        raise RuntimeError(f"empty capital flow response for {code}")
    latest = rows[-1]
    recent = {
        "3d_main_net_inflow_yi": sum_recent(rows, 3, "main_net_inflow"),
        "5d_main_net_inflow_yi": sum_recent(rows, 5, "main_net_inflow"),
        "10d_main_net_inflow_yi": sum_recent(rows, 10, "main_net_inflow"),
        "20d_main_net_inflow_yi": sum_recent(rows, 20, "main_net_inflow"),
    }
    latest_main_yi = yuan_to_yi(latest.get("main_net_inflow"))
    return {
        "code": data.get("code") or code,
        "name": data.get("name"),
        "exchange": "SSE" if code.startswith(("6", "9")) else "SZSE",
        "provider": "eastmoney",
        "status": "passed",
        "data_time": latest.get("date"),
        "window_days": days,
        "latest": normalize_day(latest),
        "recent": recent,
        "summary": {
            "today_main_net_inflow_yi": latest_main_yi,
            "today_bias": flow_bias(latest_main_yi),
            "recent_20d_main_net_inflow_yi": recent["20d_main_net_inflow_yi"],
            "recent_5d_main_net_inflow_yi": recent["5d_main_net_inflow_yi"],
            "interpretation_boundary": "资金流仅反映指定来源和口径下的净流入/净流出，不等于买卖建议；不能脱离价格位置、成交额、板块热度和基本面单独下结论。",
        },
        "history": [normalize_day(row) for row in rows],
        "source": {
            "source_name": "东方财富资金流",
            "source_type": "capital_flow",
            "stability_tier": "S3",
            "url": "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get",
            "accessed_at": datetime.now().astimezone().isoformat(),
            "limitations": "公开网页资金流接口，字段和可用性可能变化；输出为净流入口径，不能反推完整主力流入/流出总额。",
        },
    }


def flash_value(items: list[dict[str, Any]], name: str) -> float | None:
    for item in items:
        if item.get("name") == name:
            return to_float(item.get("sr"))
    return None


def fetch_ths_realtime_flow(code: str, timeout: int) -> dict[str, Any]:
    url = f"https://stockpage.10jqka.com.cn/spService/{code}/Funds/realFunds/free/1/"
    payload = fetch_json_url(url, timeout=timeout, referer=f"https://stockpage.10jqka.com.cn/{code}/funds/")
    title = payload.get("title") or {}
    flash = payload.get("flash") or []
    field = payload.get("field") or {}
    total_in_wan = to_float(title.get("zlr"))
    total_out_wan = to_float(title.get("zlc"))
    net_wan = to_float(title.get("je"))
    large_in_wan = flash_value(flash, "大单流入")
    large_out_wan = flash_value(flash, "大单流出")
    medium_in_wan = flash_value(flash, "中单流入")
    medium_out_wan = flash_value(flash, "中单流出")
    small_in_wan = flash_value(flash, "小单流入")
    small_out_wan = flash_value(flash, "小单流出")
    return {
        "code": code,
        "provider": "ths",
        "status": "passed",
        "data_time": datetime.now().astimezone().isoformat(),
        "summary": {
            "today_main_net_inflow_yi": wan_to_yi(net_wan),
            "today_bias": flow_bias(wan_to_yi(net_wan)),
            "recent_20d_main_net_inflow_yi": None,
            "recent_5d_main_net_inflow_yi": None,
            "interpretation_boundary": "同花顺实时资金流只作为盘中流入/流出增强字段；缺少历史趋势时，不得替代 3/5/10/20 日资金判断。",
        },
        "realtime": {
            "total_inflow_yi": wan_to_yi(total_in_wan),
            "total_outflow_yi": wan_to_yi(total_out_wan),
            "net_inflow_yi": wan_to_yi(net_wan),
            "order_flow_yi": {
                "large_in": wan_to_yi(large_in_wan),
                "large_out": wan_to_yi(large_out_wan),
                "large_net": wan_to_yi((large_in_wan or 0) - (large_out_wan or 0)) if large_in_wan is not None or large_out_wan is not None else None,
                "medium_in": wan_to_yi(medium_in_wan),
                "medium_out": wan_to_yi(medium_out_wan),
                "medium_net": wan_to_yi((medium_in_wan or 0) - (medium_out_wan or 0)) if medium_in_wan is not None or medium_out_wan is not None else None,
                "small_in": wan_to_yi(small_in_wan),
                "small_out": wan_to_yi(small_out_wan),
                "small_net": wan_to_yi((small_in_wan or 0) - (small_out_wan or 0)) if small_in_wan is not None or small_out_wan is not None else None,
            },
        },
        "field": {
            "industry_name": field.get("hyname"),
            "industry_net_inflow_yi": wan_to_yi(to_float(field.get("hyje"))),
        },
        "source": {
            "source_name": "同花顺资金流",
            "source_type": "capital_flow",
            "stability_tier": "S4",
            "url": url,
            "accessed_at": datetime.now().astimezone().isoformat(),
            "limitations": "同花顺公开网页服务接口，可能受 cookie、Referer、反爬和字段变化影响；仅作可选增强源，不作为 cron 唯一依赖。",
        },
    }


def parse_market_rows(html: str, limit: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    tbody_match = re.search(r"<tbody>(.*?)</tbody>", html, re.S | re.I)
    if not tbody_match:
        return items
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tbody_match.group(1), re.S | re.I)
    for row_html in rows:
        row = []
        for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S | re.I):
            text = re.sub(r"<!--.*?-->", "", cell, flags=re.S)
            text = re.sub(r"<[^>]+>", "", text)
            row.append(re.sub(r"\s+", " ", text).strip())
        if len(row) < 10 or not row[0].isdigit():
            continue
        items.append(
            {
                "rank": int(row[0]),
                "code": row[1],
                "name": row[2],
                "latest_price": to_float(row[3]),
                "pct_change": to_float(row[4].rstrip("%")) if row[4] else None,
                "turnover_rate": row[5],
                "inflow_yi": amount_to_yi(row[6]),
                "outflow_yi": amount_to_yi(row[7]),
                "net_inflow_yi": amount_to_yi(row[8]),
                "turnover_yi": amount_to_yi(row[9]),
            }
        )
        if len(items) >= limit:
            break
    return items


def parse_js_data(html: str) -> list[dict[str, Any]]:
    match = re.search(r"var\s+JS_DATA\s*=\s*(\[.*?\]);", html, re.S)
    if not match:
        return []
    data = json.loads(match.group(1))
    result = []
    for item in data:
        amount = to_float(item.get("amount"))
        result.append(
            {
                "name": item.get("name"),
                "net_inflow_yi": amount,
                "url": item.get("addr"),
            }
        )
    return result


def fetch_ths_direction_page(kind: str, timeout: int) -> dict[str, Any]:
    path = "hyzjl" if kind == "industry" else "gnzjl"
    url = f"https://data.10jqka.com.cn/funds/{path}/"
    html = fetch_text_url(url, timeout=timeout, referer="https://data.10jqka.com.cn/funds/ggzjl/")
    flows = parse_js_data(html)
    if not flows:
        raise RuntimeError(f"empty Tonghuashun {kind} flow JS_DATA")
    inflow = [item for item in flows if (item.get("net_inflow_yi") or 0) > 0]
    outflow = [item for item in flows if (item.get("net_inflow_yi") or 0) < 0]
    return {
        "kind": kind,
        "url": url,
        "items": flows,
        "top_net_inflow": sorted(inflow, key=lambda item: item.get("net_inflow_yi") or 0, reverse=True)[:10],
        "top_net_outflow": sorted(outflow, key=lambda item: item.get("net_inflow_yi") or 0)[:10],
    }


def fetch_ths_market_flow(limit: int, timeout: int) -> dict[str, Any]:
    industry = fetch_ths_direction_page("industry", timeout)
    concept = fetch_ths_direction_page("concept", timeout)
    return {
        "provider": "ths",
        "scope": "market",
        "status": "passed",
        "data_time": datetime.now().astimezone().isoformat(),
        "is_market_total": False,
        "scope_note": "大盘资金方向使用同花顺行业资金与概念资金 JS_DATA 观察资金流向，不提供全市场精确总流入/总流出。",
        "industry_flow": {
            "top_net_inflow": industry["top_net_inflow"][:limit],
            "top_net_outflow": industry["top_net_outflow"][:limit],
            "source_url": industry["url"],
        },
        "concept_flow": {
            "top_net_inflow": concept["top_net_inflow"][:limit],
            "top_net_outflow": concept["top_net_outflow"][:limit],
            "source_url": concept["url"],
        },
        "summary": {
            "strong_industries": industry["top_net_inflow"][:5],
            "weak_industries": industry["top_net_outflow"][:5],
            "strong_concepts": concept["top_net_inflow"][:5],
            "weak_concepts": concept["top_net_outflow"][:5],
            "interpretation_boundary": "这是行业/概念资金方向，不是全市场资金净流入总额；不得写成大盘总流入、总流出或全市场净额。",
        },
        "source": {
            "source_name": "同花顺行业/概念资金流向",
            "source_type": "market_capital_flow",
            "stability_tier": "S4",
            "url": "https://data.10jqka.com.cn/funds/hyzjl/ ; https://data.10jqka.com.cn/funds/gnzjl/",
            "accessed_at": datetime.now().astimezone().isoformat(),
            "limitations": "公开网页 JS_DATA，适合观察行业/概念资金方向；不提供全市场精确资金总额，不能替代授权行情终端的大盘资金统计。",
        },
    }


def merge_auto_flow(code: str, days: int, timeout: int) -> dict[str, Any]:
    provider_results: list[dict[str, Any]] = []
    try:
        base = fetch_eastmoney_stock_flow(code, days, timeout)
        provider_results.append({"provider": "eastmoney", "status": "passed"})
    except Exception as exc:  # noqa: BLE001 - auto mode should try realtime fallback
        base = {}
        provider_results.append({"provider": "eastmoney", "status": "degraded", "error": str(exc)})
    try:
        ths = fetch_ths_realtime_flow(code, min(timeout, 8))
        if not base:
            base = ths
            base["sources"] = [ths.get("source")]
        else:
            base["realtime"] = ths.get("realtime")
            base["field"] = ths.get("field")
            base.setdefault("sources", [base.get("source")])
            base["sources"].append(ths.get("source"))
        provider_results.append({"provider": "ths", "status": "passed"})
        base["provider"] = "auto"
    except Exception as exc:  # noqa: BLE001 - optional provider should not break main flow
        provider_results.append({"provider": "ths", "status": "degraded", "error": str(exc)})
        if not base:
            raise RuntimeError("all capital flow providers failed")
        base.setdefault("warnings", []).append("ths realtime flow unavailable; kept eastmoney daily net flow")
    base["provider_results"] = provider_results
    return base


def fetch_provider(provider: str, code: str, days: int, timeout: int) -> dict[str, Any]:
    if provider == "auto":
        return merge_auto_flow(code, days, timeout)
    if provider == "eastmoney":
        return fetch_eastmoney_stock_flow(code, days, timeout)
    if provider == "ths":
        return fetch_ths_realtime_flow(code, timeout)
    raise ValueError(f"unknown capital flow provider: {provider}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch A-share capital-flow data")
    parser.add_argument("codes", nargs="*", help="A-share stock codes, e.g. 300308 600519")
    parser.add_argument("--scope", choices=["stock", "market"], default="stock")
    parser.add_argument("--provider", choices=["auto", "eastmoney", "ths"], default="auto")
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--limit", type=int, default=50, help="Market ranking rows to parse when --scope market")
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--output", "-o", default="runtime/capital-flow.latest.json")
    parser.add_argument("--require-results", action="store_true")
    args = parser.parse_args()

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    if args.scope == "market":
        try:
            results.append(fetch_ths_market_flow(args.limit, args.timeout))
        except Exception as exc:  # noqa: BLE001 - command-line diagnostics
            errors.append({"scope": "market", "provider": "ths", "error": str(exc)})
    else:
        if not args.codes:
            raise SystemExit("stock scope requires at least one code")
        for code in args.codes:
            try:
                results.append(fetch_provider(args.provider, code, args.days, args.timeout))
            except Exception as exc:  # noqa: BLE001 - command-line diagnostics
                errors.append({"code": code, "provider": args.provider, "error": str(exc)})

    status = "passed" if results and not errors else "degraded" if results else "failed"
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "scope": args.scope,
        "provider": args.provider,
        "status": status,
        "results": results,
        "errors": errors,
        "warnings": [] if results else ["no capital flow data available"],
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
