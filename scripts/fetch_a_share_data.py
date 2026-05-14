#!/usr/bin/env python3
"""Fetch A-share quote data from multiple providers for runtime artifacts.

The default path intentionally keeps dependencies to Python stdlib. Sina and
Tencent are fast public quote providers used for cron-friendly cross-checks.
Eastmoney stays available as a richer S3 source, and optional SDK providers can
be enabled without changing the downstream recommendation schema.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


QuoteProvider = Callable[[str], dict[str, Any]]


def secid_for(code: str) -> str:
    code = code.strip()
    if code.startswith(("6", "9")):
        return f"1.{code}"
    if code.startswith(("0", "2", "3")):
        return f"0.{code}"
    if code.startswith(("4", "8")):
        return f"0.{code}"
    raise ValueError(f"cannot infer exchange for code: {code}")


def fetch_json(url: str, params: dict[str, str], timeout: int = 10, retries: int = 2) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) lobster-invest/1.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://quote.eastmoney.com/",
            "Connection": "close",
        },
    )
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - provider diagnostics must retain original failure
            last_exc = exc
            if attempt < retries:
                time.sleep(0.3 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def scaled_price(value: Any) -> float | None:
    if value in (None, "-", ""):
        return None
    try:
        number = float(value)
        if abs(number) > 1000:
            number = number / 100
        return round(number, 4)
    except (TypeError, ValueError):
        return None


def fetch_quote(code: str) -> dict[str, Any]:
    fields = ",".join(
        [
            "f43",  # latest
            "f44",  # high
            "f45",  # low
            "f46",  # open
            "f47",  # volume
            "f48",  # turnover
            "f57",  # code
            "f58",  # name
            "f60",  # previous close
            "f86",  # timestamp
            "f169",  # change
            "f170",  # pct change
        ]
    )
    payload = fetch_json(
        "https://push2.eastmoney.com/api/qt/stock/get",
        {"secid": secid_for(code), "fields": fields, "fltt": "2"},
    )
    data = payload.get("data") or {}
    if not data:
        raise RuntimeError(f"empty quote response for {code}")

    timestamp = data.get("f86")
    data_time = None
    if timestamp:
        try:
            data_time = datetime.fromtimestamp(int(timestamp), timezone.utc).astimezone().isoformat()
        except (TypeError, ValueError, OSError):
            data_time = str(timestamp)

    result = {
        "code": str(data.get("f57") or code),
        "name": data.get("f58"),
        "exchange": "SSE" if code.startswith("6") else "SZSE",
        "latest_price": scaled_price(data.get("f43")),
        "previous_close": scaled_price(data.get("f60")),
        "open": scaled_price(data.get("f46")),
        "high": scaled_price(data.get("f44")),
        "low": scaled_price(data.get("f45")),
        "volume": data.get("f47"),
        "turnover": data.get("f48"),
        "change": scaled_price(data.get("f169")),
        "pct_change": scaled_price(data.get("f170")),
        "data_time": data_time,
        "source": {
            "source_name": "东方财富",
            "source_type": "market_data",
            "stability_tier": "S3",
            "url": "https://push2.eastmoney.com/api/qt/stock/get",
            "accessed_at": datetime.now().astimezone().isoformat(),
            "limitations": "公开网页行情接口，字段和可用性可能变化；09:00 任务应优先使用 previous_close。",
        },
    }
    return result


def fetch_quote_eastmoney(code: str) -> dict[str, Any]:
    return fetch_quote(code)


def tencent_symbol(code: str) -> str:
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


def fetch_quote_tencent(code: str) -> dict[str, Any]:
    url = f"https://qt.gtimg.cn/q={tencent_symbol(code)}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 lobster-invest/1.0", "Referer": "https://gu.qq.com/"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        text = response.read().decode("gbk", "ignore")
    if '="' not in text:
        raise RuntimeError(f"unexpected tencent quote response for {code}")
    body = text.split('="', 1)[1].rsplit('"', 1)[0]
    parts = body.split("~")
    if len(parts) < 33:
        raise RuntimeError(f"incomplete tencent quote response for {code}")

    def field(index: int) -> str | None:
        return parts[index] if index < len(parts) and parts[index] != "" else None

    timestamp = field(30)
    data_time = timestamp
    if timestamp and len(timestamp) == 14:
        try:
            data_time = datetime.strptime(timestamp, "%Y%m%d%H%M%S").astimezone().isoformat()
        except ValueError:
            data_time = timestamp

    return {
        "code": field(2) or code,
        "name": field(1),
        "exchange": "SSE" if code.startswith("6") else "SZSE",
        "latest_price": float(field(3)) if field(3) else None,
        "previous_close": float(field(4)) if field(4) else None,
        "open": float(field(5)) if field(5) else None,
        "high": float(field(33)) if field(33) else None,
        "low": float(field(34)) if field(34) else None,
        "volume": field(36),
        "turnover": field(37),
        "change": float(field(31)) if field(31) else None,
        "pct_change": float(field(32)) if field(32) else None,
        "data_time": data_time,
        "source": {
            "source_name": "腾讯行情",
            "source_type": "market_data",
            "stability_tier": "S4",
            "url": "https://qt.gtimg.cn/q=",
            "accessed_at": datetime.now().astimezone().isoformat(),
            "limitations": "公开网页行情接口，仅作东方财富不可用时的补充或交叉校验。",
        },
    }


def sina_symbol(code: str) -> str:
    if code.startswith(("6", "9")):
        return f"sh{code}"
    return f"sz{code}"


def to_float(value: Any) -> float | None:
    if value in (None, "-", ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_quote_sina(code: str) -> dict[str, Any]:
    symbol = sina_symbol(code)
    url = f"https://hq.sinajs.cn/list={symbol}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 lobster-invest/1.0",
            "Referer": "https://finance.sina.com.cn/",
        },
    )
    with urllib.request.urlopen(request, timeout=6) as response:
        text = response.read().decode("gbk", "ignore")
    if '="' not in text:
        raise RuntimeError(f"unexpected sina quote response for {code}")
    body = text.split('="', 1)[1].rsplit('"', 1)[0]
    parts = body.split(",")
    if len(parts) < 32 or not parts[0]:
        raise RuntimeError(f"incomplete sina quote response for {code}")

    date = parts[30] if len(parts) > 30 else ""
    quote_time = parts[31] if len(parts) > 31 else ""
    data_time = f"{date}T{quote_time}" if date and quote_time else None
    if data_time:
        try:
            data_time = datetime.strptime(f"{date} {quote_time}", "%Y-%m-%d %H:%M:%S").astimezone().isoformat()
        except ValueError:
            data_time = f"{date} {quote_time}".strip()

    latest = to_float(parts[3])
    previous_close = to_float(parts[2])
    change = round(latest - previous_close, 4) if latest is not None and previous_close not in (None, 0) else None
    pct_change = round(change / previous_close * 100, 4) if change is not None and previous_close not in (None, 0) else None
    return {
        "code": code,
        "name": parts[0],
        "exchange": "SSE" if code.startswith("6") else "SZSE",
        "latest_price": latest,
        "previous_close": previous_close,
        "open": to_float(parts[1]),
        "high": to_float(parts[4]),
        "low": to_float(parts[5]),
        "volume": parts[8] if len(parts) > 8 else None,
        "turnover": parts[9] if len(parts) > 9 else None,
        "change": change,
        "pct_change": pct_change,
        "data_time": data_time,
        "source": {
            "source_name": "新浪财经",
            "source_type": "market_data",
            "stability_tier": "S4",
            "url": "https://hq.sinajs.cn/list=",
            "accessed_at": datetime.now().astimezone().isoformat(),
            "limitations": "公开网页行情接口，速度快但无官方稳定承诺；用于 cron 快速行情和交叉校验。",
        },
    }


def first_present(row: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in row and row[name] not in (None, "", "-"):
            return row[name]
    return None


def fetch_quote_adata(code: str) -> dict[str, Any]:
    try:
        import adata  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("adata is not installed; run `python3 -m pip install -U adata` to enable this provider") from exc

    frame = adata.stock.market.list_market_current(code_list=[code])
    if frame is None or getattr(frame, "empty", True):
        raise RuntimeError(f"adata returned empty quote response for {code}")
    row = frame.head(1).to_dict(orient="records")[0]
    latest = to_float(first_present(row, ["price", "close", "最新价", "现价", "收盘价"]))
    previous_close = to_float(first_present(row, ["pre_close", "prev_close", "昨收", "昨收价", "previous_close"]))
    change = to_float(first_present(row, ["change", "涨跌额", "涨跌"]))
    pct_change = to_float(first_present(row, ["change_pct", "涨跌幅", "pct_change", "increase"]))
    if change is None and latest is not None and previous_close not in (None, 0):
        change = round(latest - previous_close, 4)
    if pct_change is None and change is not None and previous_close not in (None, 0):
        pct_change = round(change / previous_close * 100, 4)

    return {
        "code": str(first_present(row, ["stock_code", "code", "股票代码"]) or code),
        "name": first_present(row, ["short_name", "name", "股票简称", "名称"]),
        "exchange": "SSE" if code.startswith("6") else "SZSE",
        "latest_price": latest,
        "previous_close": previous_close,
        "open": to_float(first_present(row, ["open", "今开", "开盘价"])),
        "high": to_float(first_present(row, ["high", "最高", "最高价"])),
        "low": to_float(first_present(row, ["low", "最低", "最低价"])),
        "volume": first_present(row, ["volume", "成交量"]),
        "turnover": first_present(row, ["amount", "turnover", "成交额"]),
        "change": change,
        "pct_change": pct_change,
        "data_time": first_present(row, ["trade_time", "datetime", "time", "更新时间", "交易时间"]),
        "source": {
            "source_name": "adata",
            "source_type": "market_data",
            "stability_tier": "S2",
            "url": "https://github.com/1nchaos/adata",
            "accessed_at": datetime.now().astimezone().isoformat(),
            "limitations": "Apache-2.0 开源 SDK，多数据源封装；底层仍可能依赖公开网页接口，需保留 provider_results 交叉校验。",
        },
        "raw_fields": row,
    }


QUOTE_PROVIDERS: dict[str, QuoteProvider] = {
    "sina": fetch_quote_sina,
    "adata": fetch_quote_adata,
    "eastmoney": fetch_quote_eastmoney,
    "tencent": fetch_quote_tencent,
}


def normalize_providers(value: str) -> list[str]:
    providers = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = [item for item in providers if item not in QUOTE_PROVIDERS]
    if unknown:
        raise ValueError(f"unknown quote provider(s): {', '.join(unknown)}")
    return providers


def provider_rank(result: dict[str, Any]) -> tuple[int, str]:
    tier = ((result.get("source") or {}).get("stability_tier") or "S9").upper()
    try:
        rank = int(tier[1:])
    except (ValueError, IndexError):
        rank = 9
    return rank, (result.get("source") or {}).get("source_name") or ""


def pct_diff(left: float | None, right: float | None) -> float | None:
    if left in (None, 0) or right is None:
        return None
    return round(abs(left - right) / abs(left) * 100, 4)


def cross_check_quotes(results: list[dict[str, Any]], max_price_diff_pct: float) -> dict[str, Any]:
    warnings: list[str] = []
    valid = [item for item in results if item.get("status") == "ok" and item.get("quote")]
    if not valid:
        return {"status": "failed", "warnings": ["no provider returned quote data"], "checks": []}
    if len(valid) == 1:
        source_name = (valid[0]["quote"].get("source") or {}).get("source_name", valid[0]["provider"])
        return {
            "status": "single_source",
            "warnings": [f"only {source_name} returned quote data; downgrade confidence"],
            "checks": [],
        }

    selected = sorted((item["quote"] for item in valid), key=provider_rank)[0]
    checks = []
    for item in valid:
        quote = item["quote"]
        if quote is selected:
            continue
        for field in ["latest_price", "previous_close", "open", "high", "low"]:
            diff = pct_diff(selected.get(field), quote.get(field))
            if diff is None:
                continue
            check = {
                "field": field,
                "primary": selected.get(field),
                "provider": item["provider"],
                "provider_value": quote.get(field),
                "diff_pct": diff,
            }
            checks.append(check)
            if diff > max_price_diff_pct:
                warnings.append(f"{field} differs by {diff}% between primary and {item['provider']}")

    status = "passed" if not warnings else "conflict"
    return {"status": status, "warnings": warnings, "checks": checks}


def fetch_quote_multi(code: str, providers: list[str], max_price_diff_pct: float) -> dict[str, Any]:
    provider_results = []
    for provider in providers:
        try:
            quote = QUOTE_PROVIDERS[provider](code)
            provider_results.append({"provider": provider, "status": "ok", "quote": quote})
        except Exception as exc:  # noqa: BLE001 - provider diagnostics must be retained
            provider_results.append({"provider": provider, "status": "error", "error": str(exc)})

    ok_quotes = [item["quote"] for item in provider_results if item.get("status") == "ok" and item.get("quote")]
    if not ok_quotes:
        raise RuntimeError(f"all quote providers failed for {code}")
    selected = sorted(ok_quotes, key=provider_rank)[0]
    quality = cross_check_quotes(provider_results, max_price_diff_pct)
    merged = dict(selected)
    merged["provider_results"] = provider_results
    merged["quality"] = quality
    merged["source_policy"] = "primary provider by stability tier; other providers used for cross-check"
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch lightweight A-share quotes")
    parser.add_argument("codes", nargs="+", help="A-share stock codes, e.g. 000001 600000")
    parser.add_argument("--output", "-o", default="runtime/market-data/latest-quotes.json")
    parser.add_argument(
        "--providers",
        default="sina,tencent",
        help=f"Comma-separated quote providers. Available: {', '.join(QUOTE_PROVIDERS)}",
    )
    parser.add_argument("--max-price-diff-pct", type=float, default=0.5)
    args = parser.parse_args()
    providers = normalize_providers(args.providers)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    quotes = []
    errors = []
    for code in args.codes:
        try:
            quotes.append(fetch_quote_multi(code, providers, args.max_price_diff_pct))
            time.sleep(0.2)
        except Exception as exc:  # noqa: BLE001 - command-line diagnostics
            errors.append({"code": code, "error": str(exc)})

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_policy": "Provider registry: Sina/Tencent fast cron quotes by default; use Eastmoney S3 or optional adata SDK explicitly for enrichment.",
        "providers": providers,
        "max_price_diff_pct": args.max_price_diff_pct,
        "quotes": quotes,
        "errors": errors,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Quotes: {len(quotes)}")
    if errors:
        print(f"Errors: {len(errors)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
