#!/usr/bin/env python3
"""Run repeatable connectivity checks for A-share runtime providers."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]


def run_command(name: str, command: list[str], timeout_sec: int = 30) -> dict[str, Any]:
    started = time.time()
    try:
        process = subprocess.run(  # noqa: S603 - commands are static repo-local checks
            command,
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
            check=False,
        )
        return {
            "name": name,
            "command": command,
            "exit_code": process.returncode,
            "duration_sec": round(time.time() - started, 3),
            "stdout": process.stdout,
            "stderr": process.stderr,
            "timeout_sec": timeout_sec,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "command": command,
            "exit_code": None,
            "duration_sec": round(time.time() - started, 3),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout_sec": timeout_sec,
            "error": f"check timed out after {timeout_sec}s",
        }


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - diagnostics should keep failed artifact details
        return {"_load_error": str(exc)}


def check_package(tmpdir: Path) -> dict[str, Any]:
    command = run_command("validate_package", ["bash", "scripts/validate_package.sh"], timeout_sec=30)
    return {
        "status": "passed" if command["exit_code"] == 0 else "failed",
        "command": command,
    }


def check_quotes(tmpdir: Path) -> dict[str, Any]:
    output = tmpdir / "quotes.json"
    command = run_command(
        "fetch_a_share_data",
        ["python3", "scripts/fetch_a_share_data.py", "000001", "600519", "--output", str(output)],
        timeout_sec=20,
    )
    payload = load_json(output)
    quotes = payload.get("quotes") or []
    provider_ok = []
    for quote in quotes:
        provider_ok.extend(
            item.get("status") == "ok" for item in quote.get("provider_results", []) if item.get("provider") in {"sina", "tencent"}
        )
    passed = command["exit_code"] == 0 and len(quotes) >= 2 and provider_ok and all(provider_ok)
    return {
        "status": "passed" if passed else "failed",
        "quote_count": len(quotes),
        "providers": payload.get("providers"),
        "errors": payload.get("errors"),
        "quotes": [
            {
                "code": item.get("code"),
                "name": item.get("name"),
                "latest_price": item.get("latest_price"),
                "data_time": item.get("data_time"),
                "quality": (item.get("quality") or {}).get("status"),
                "provider_results": [
                    {"provider": result.get("provider"), "status": result.get("status"), "error": result.get("error")}
                    for result in item.get("provider_results", [])
                ],
            }
            for item in quotes
        ],
        "command": command,
    }


def check_capital_flow(tmpdir: Path) -> dict[str, Any]:
    output = tmpdir / "capital-flow.json"
    command = run_command(
        "fetch_capital_flow",
        ["python3", "scripts/fetch_capital_flow.py", "300308", "--provider", "auto", "--days", "20", "--output", str(output)],
        timeout_sec=25,
    )
    payload = load_json(output)
    results = payload.get("results") or []
    passed = command["exit_code"] == 0 and payload.get("status") in {"passed", "degraded"} and len(results) > 0
    first = results[0] if results else {}
    return {
        "status": "passed" if passed else "failed",
        "provider": payload.get("provider"),
        "result_count": len(results),
        "errors": payload.get("errors"),
        "provider_results": first.get("provider_results"),
        "summary": first.get("summary"),
        "realtime": first.get("realtime"),
        "command": command,
    }


def check_sector(tmpdir: Path, kind: str) -> dict[str, Any]:
    output = tmpdir / f"sector-{kind}.json"
    command = run_command(
        f"fetch_sector_boards_{kind}",
        ["python3", "scripts/fetch_sector_boards.py", "--provider", "auto", "--kind", kind, "--limit", "5", "--output", str(output)],
        timeout_sec=25,
    )
    payload = load_json(output)
    boards = payload.get("boards") or []
    passed = command["exit_code"] == 0 and payload.get("status") == "passed" and len(boards) > 0
    return {
        "status": "passed" if passed else "failed",
        "provider": payload.get("provider"),
        "board_count": len(boards),
        "errors": payload.get("errors"),
        "boards": [
            {
                "board_code": item.get("board_code"),
                "name": item.get("name"),
                "pct_change": item.get("pct_change"),
                "leading_stock": item.get("leading_stock"),
                "leading_stock_pct_change": item.get("leading_stock_pct_change"),
            }
            for item in boards
        ],
        "command": command,
    }


def check_news(tmpdir: Path) -> dict[str, Any]:
    output = tmpdir / "news.json"
    command = run_command(
        "search_news",
        [
            "python3",
            "scripts/search_news.py",
            "半导体 政策 催化",
            "--timeout",
            "4",
            "--overall-timeout",
            "12",
            "--max-results",
            "3",
            "--output",
            str(output),
        ],
        timeout_sec=18,
    )
    payload = load_json(output)
    results = payload.get("results") or []
    passed = command["exit_code"] == 0 and payload.get("status") == "passed" and len(results) > 0
    return {
        "status": "passed" if passed else "failed",
        "result_count": len(results),
        "provider_results": payload.get("provider_results"),
        "results": [
            {
                "title": item.get("title"),
                "provider": item.get("provider"),
                "published_at": item.get("published_at"),
                "url": item.get("url"),
            }
            for item in results
        ],
        "command": command,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"Connectivity check: {report['status']}",
        f"Generated at: {report['generated_at']}",
        "",
    ]
    for name, check in report["checks"].items():
        lines.append(f"{name}: {check['status']}")
        if name == "quotes":
            lines.append(f"  providers={check.get('providers')} quote_count={check.get('quote_count')}")
            for quote in check.get("quotes", []):
                lines.append(
                    f"  {quote['code']} {quote['name']} price={quote['latest_price']} time={quote['data_time']} quality={quote['quality']}"
                )
        elif name == "capital_flow":
            lines.append(f"  provider={check.get('provider')} result_count={check.get('result_count')}")
            summary = check.get("summary") or {}
            lines.append(
                f"  today_main_net={summary.get('today_main_net_inflow_yi')}亿 5d={summary.get('recent_5d_main_net_inflow_yi')}亿 20d={summary.get('recent_20d_main_net_inflow_yi')}亿"
            )
            realtime = check.get("realtime") or {}
            if realtime:
                lines.append(
                    f"  ths_total_in={realtime.get('total_inflow_yi')}亿 ths_total_out={realtime.get('total_outflow_yi')}亿 net={realtime.get('net_inflow_yi')}亿"
                )
            if check.get("provider_results"):
                lines.append(f"  provider_results={check.get('provider_results')}")
        elif name.startswith("sector"):
            lines.append(f"  provider={check.get('provider')} board_count={check.get('board_count')}")
            for board in check.get("boards", [])[:3]:
                lines.append(
                    f"  {board['name']} pct_change={board['pct_change']} leading={board['leading_stock']}"
                )
            if check.get("errors"):
                lines.append(f"  degraded_errors={check.get('errors')}")
        elif name == "news":
            lines.append(f"  result_count={check.get('result_count')}")
            for item in check.get("results", [])[:3]:
                lines.append(f"  {item['title']} | {item['provider']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check runtime connectivity for A-share skills")
    parser.add_argument("--output", "-o", default="runtime/connectivity-check.latest.json")
    parser.add_argument("--text-output", default="")
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT_DIR / output
    tmpdir = output.parent / ".connectivity-tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)

    checks = {
        "package": check_package(tmpdir),
        "quotes": check_quotes(tmpdir),
        "capital_flow": check_capital_flow(tmpdir),
        "sector_concept": check_sector(tmpdir, "concept"),
        "sector_industry": check_sector(tmpdir, "industry"),
        "news": check_news(tmpdir),
    }
    status = "passed" if all(item.get("status") == "passed" for item in checks.values()) else "failed"
    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": status,
        "checks": checks,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    text = render_text(report)
    if args.text_output:
        text_output = Path(args.text_output)
        if not text_output.is_absolute():
            text_output = ROOT_DIR / text_output
        text_output.parent.mkdir(parents=True, exist_ok=True)
        text_output.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"Wrote {output}")
    return 0 if status == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
