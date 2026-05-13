#!/usr/bin/env python3
"""Fetch lightweight A-share market data for runtime artifacts.

This script intentionally keeps dependencies to Python stdlib. It uses public
Eastmoney quote endpoints as a best-effort S3 data source and records source
metadata for later evidence checks. For official announcements/financials, use
S1 sources manually or through a dedicated provider.
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
from typing import Any


def secid_for(code: str) -> str:
    code = code.strip()
    if code.startswith(("6", "9")):
        return f"1.{code}"
    if code.startswith(("0", "2", "3")):
        return f"0.{code}"
    if code.startswith(("4", "8")):
        return f"0.{code}"
    raise ValueError(f"cannot infer exchange for code: {code}")


def fetch_json(url: str, params: dict[str, str], timeout: int = 10) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={
            "User-Agent": "Mozilla/5.0 lobster-invest/1.0",
            "Referer": "https://quote.eastmoney.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch lightweight A-share quotes")
    parser.add_argument("codes", nargs="+", help="A-share stock codes, e.g. 000001 600000")
    parser.add_argument("--output", "-o", default="runtime/market-data/latest-quotes.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    quotes = []
    errors = []
    for code in args.codes:
        try:
            try:
                quotes.append(fetch_quote(code))
            except Exception:
                quotes.append(fetch_quote_tencent(code))
            time.sleep(0.2)
        except Exception as exc:  # noqa: BLE001 - command-line diagnostics
            errors.append({"code": code, "error": str(exc)})

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_policy": "S3 Eastmoney quote endpoint; cross-check important fields before high-confidence output.",
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
