#!/usr/bin/env python3
"""Fetch A-share sector board snapshots from Eastmoney or optional SDKs.

Eastmoney public endpoints are used as the dependency-free default. Tonghuashun
board data is routed through AKShare when installed, because there is no stable
free official Tonghuashun API contract suitable for direct hard-coding here.
adata can also be enabled as an optional Apache-2.0 SDK provider for Eastmoney
and Tonghuashun concept board snapshots.
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
    status = "passed" if boards else "degraded"
    warnings = [] if boards else ["eastmoney board endpoint returned empty board list"]
    return {
        "provider": "eastmoney",
        "kind": kind,
        "status": status,
        "warnings": warnings,
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
    status = "passed" if records else "degraded"
    warnings = [] if records else ["akshare_ths returned empty board list"]
    return {
        "provider": "akshare_ths",
        "kind": kind,
        "status": status,
        "warnings": warnings,
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


def first_present(row: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in row and row[name] not in (None, "", "-"):
            return row[name]
    return None


def normalize_adata_board_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "board_code": first_present(row, ["concept_code", "plate_code", "code", "板块代码", "概念代码"]),
        "name": first_present(row, ["concept_name", "plate_name", "name", "板块名称", "概念名称", "名称"]),
        "pct_change": normalize_number(first_present(row, ["change_pct", "涨跌幅", "increase", "pct_change"])),
        "change": normalize_number(first_present(row, ["change", "涨跌额", "涨跌"])),
        "turnover": normalize_number(first_present(row, ["amount", "turnover", "成交额"])),
        "market_value": normalize_number(first_present(row, ["market_value", "总市值"])),
        "main_net_inflow": normalize_number(first_present(row, ["main_net_inflow", "主力净流入"])),
        "rise_count": normalize_number(first_present(row, ["rise_count", "上涨家数"])),
        "fall_count": normalize_number(first_present(row, ["fall_count", "下跌家数"])),
        "leading_stock": first_present(row, ["leader_stock", "leading_stock", "领涨股"]),
        "leading_stock_pct_change": normalize_number(first_present(row, ["leader_stock_pct", "leading_stock_pct_change", "领涨股涨跌幅"])),
        "raw_fields": row,
    }


def fetch_adata_boards(provider: str, kind: str, limit: int) -> dict[str, Any]:
    try:
        import adata  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("adata is not installed; run `python3 -m pip install -U adata` to enable this provider") from exc

    if kind != "concept":
        raise ValueError("adata board providers currently support concept boards only")
    if provider == "adata_east":
        frame = adata.stock.market.get_market_concept_current_east()
        source_name = "adata-东方财富概念"
    elif provider == "adata_ths":
        frame = adata.stock.market.get_market_concept_current_ths()
        source_name = "adata-同花顺概念"
    else:
        raise ValueError(f"unknown adata board provider: {provider}")

    records = [] if frame is None or getattr(frame, "empty", True) else frame.head(limit).to_dict(orient="records")
    boards = [normalize_adata_board_row(item) for item in records]
    status = "passed" if boards else "degraded"
    warnings = [] if boards else [f"{provider} returned empty board list"]
    return {
        "provider": provider,
        "kind": kind,
        "status": status,
        "warnings": warnings,
        "source": {
            "source_name": source_name,
            "source_type": "sector_board",
            "stability_tier": "S2",
            "url": "https://github.com/1nchaos/adata",
            "accessed_at": datetime.now().astimezone().isoformat(),
            "limitations": "Apache-2.0 开源 SDK，多数据源封装；底层仍可能依赖公开网页结构，关键结论需交叉校验。",
        },
        "boards": boards,
    }


def fetch_provider(provider: str, kind: str, limit: int) -> dict[str, Any]:
    if provider == "eastmoney":
        return fetch_eastmoney_boards(kind, limit)
    if provider == "akshare_ths":
        return fetch_akshare_ths_boards(kind, limit)
    if provider in {"adata_east", "adata_ths"}:
        return fetch_adata_boards(provider, kind, limit)
    raise ValueError(f"unknown sector board provider: {provider}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch A-share sector board snapshots")
    parser.add_argument("--provider", choices=["auto", "eastmoney", "akshare_ths", "adata_east", "adata_ths"], default="auto")
    parser.add_argument("--kind", choices=["industry", "concept"], default="concept")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", "-o", default="runtime/market-data/sector-boards.latest.json")
    parser.add_argument("--require-results", action="store_true", help="Exit non-zero when no board data is available")
    args = parser.parse_args()

    errors: list[dict[str, str]] = []
    attempts = ["adata_east", "eastmoney", "akshare_ths", "adata_ths"] if args.provider == "auto" else [args.provider]
    payload: dict[str, Any] | None = None
    for provider in attempts:
        try:
            candidate = fetch_provider(provider, args.kind, args.limit)
            if candidate.get("boards"):
                payload = candidate
                break
            errors.append({"provider": provider, "error": "empty board list"})
            payload = payload or candidate
        except Exception as exc:  # noqa: BLE001 - command-line diagnostics
            errors.append({"provider": provider, "error": str(exc)})
    if payload is None:
        payload = {
            "provider": args.provider,
            "kind": args.kind,
            "status": "failed",
            "warnings": ["all sector board providers failed"],
            "boards": [],
        }

    payload["generated_at"] = datetime.now().astimezone().isoformat()
    payload["errors"] = errors

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
