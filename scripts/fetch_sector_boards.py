#!/usr/bin/env python3
"""Fetch A-share sector board snapshots from Eastmoney or optional AKShare.

Eastmoney public endpoints are used as the dependency-free default. Tonghuashun
board data is routed through AKShare when installed, because there is no stable
free official Tonghuashun API contract suitable for direct hard-coding here.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


EASTMONEY_BOARD_KINDS = {
    "industry": "m:90+t:2",
    "concept": "m:90+t:3",
}


def fetch_json(url: str, params: dict[str, str], timeout: int = 12, retries: int = 2) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) lobster-invest/1.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://quote.eastmoney.com/center/boardlist.html",
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


def normalize_number(value: Any) -> float | int | str | None:
    if value in (None, "-", ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return int(number)
    return round(number, 4)


def fetch_eastmoney_boards(kind: str, limit: int) -> dict[str, Any]:
    fs = EASTMONEY_BOARD_KINDS[kind]
    fields = "f12,f14,f3,f4,f6,f20,f62,f104,f105,f128,f136,f152"
    payload = fetch_json(
        "https://push2.eastmoney.com/api/qt/clist/get",
        {
            "pn": "1",
            "pz": str(limit),
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": fs,
            "fields": fields,
        },
    )
    diff = ((payload.get("data") or {}).get("diff")) or []
    boards = []
    for item in diff:
        boards.append(
            {
                "board_code": item.get("f12"),
                "name": item.get("f14"),
                "pct_change": normalize_number(item.get("f3")),
                "change": normalize_number(item.get("f4")),
                "turnover": normalize_number(item.get("f6")),
                "market_value": normalize_number(item.get("f20")),
                "main_net_inflow": normalize_number(item.get("f62")),
                "rise_count": normalize_number(item.get("f104")),
                "fall_count": normalize_number(item.get("f105")),
                "leading_stock": item.get("f128"),
                "leading_stock_pct_change": normalize_number(item.get("f136")),
            }
        )
    return {
        "provider": "eastmoney",
        "kind": kind,
        "source": {
            "source_name": "东方财富",
            "source_type": "sector_board",
            "stability_tier": "S3",
            "url": "https://push2.eastmoney.com/api/qt/clist/get",
            "accessed_at": datetime.now().astimezone().isoformat(),
            "limitations": "公开网页板块接口，参数和字段可能变化；用于板块热度初筛，关键结论需交叉校验。",
        },
        "boards": boards,
    }


def fetch_akshare_ths_boards(kind: str, limit: int) -> dict[str, Any]:
    try:
        import akshare as ak  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("akshare is not installed; cannot fetch Tonghuashun boards") from exc

    if kind == "industry":
        frame = ak.stock_board_industry_name_ths()
    elif kind == "concept":
        frame = ak.stock_board_concept_name_ths()
    else:
        raise ValueError(f"unsupported Tonghuashun board kind: {kind}")

    records = frame.head(limit).to_dict(orient="records")
    return {
        "provider": "akshare_ths",
        "kind": kind,
        "source": {
            "source_name": "AKShare-同花顺",
            "source_type": "sector_board",
            "stability_tier": "S3",
            "url": "https://akshare.akfamily.xyz/",
            "accessed_at": datetime.now().astimezone().isoformat(),
            "limitations": "通过 AKShare 封装同花顺数据；字段依赖上游网页结构，不视为官方稳定接口。",
        },
        "boards": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch A-share sector board snapshots")
    parser.add_argument("--provider", choices=["eastmoney", "akshare_ths"], default="eastmoney")
    parser.add_argument("--kind", choices=["industry", "concept"], default="concept")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", "-o", default="runtime/market-data/sector-boards.latest.json")
    args = parser.parse_args()

    errors: list[dict[str, str]] = []
    try:
        if args.provider == "eastmoney":
            payload = fetch_eastmoney_boards(args.kind, args.limit)
        else:
            payload = fetch_akshare_ths_boards(args.kind, args.limit)
    except Exception as exc:  # noqa: BLE001 - command-line diagnostics
        payload = {"provider": args.provider, "kind": args.kind, "boards": []}
        errors.append({"provider": args.provider, "error": str(exc)})

    payload["generated_at"] = datetime.now().astimezone().isoformat()
    payload["errors"] = errors

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Boards: {len(payload.get('boards') or [])}")
    if errors:
        print(f"Errors: {len(errors)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
