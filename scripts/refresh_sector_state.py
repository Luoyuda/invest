#!/usr/bin/env python3
"""Refresh sector-state with bounded runtime, cache fallback, and lock control."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def acquire_lock(lock_path: Path, stale_after_sec: int) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        age = time.time() - lock_path.stat().st_mtime
        if age <= stale_after_sec:
            raise RuntimeError(f"refresh already running; lock={lock_path}, age_sec={round(age, 1)}")
        lock_path.unlink()
    fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(f"pid={os.getpid()}\ncreated_at={now_iso()}\n")


def run_fetch(kind: str, limit: int, timeout_sec: int, output: Path) -> dict[str, Any]:
    tmp_output = output.with_suffix(".tmp.json")
    command = [
        sys.executable,
        "scripts/fetch_sector_boards.py",
        "--provider",
        "auto",
        "--kind",
        kind,
        "--limit",
        str(limit),
        "--output",
        str(tmp_output),
        "--require-results",
    ]
    started = time.time()
    result = {
        "kind": kind,
        "command": command,
        "started_at": now_iso(),
        "timeout_sec": timeout_sec,
    }
    try:
        process = subprocess.run(  # noqa: S603 - static repo-local command
            command,
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
            check=False,
        )
        result.update(
            {
                "exit_code": process.returncode,
                "duration_sec": round(time.time() - started, 3),
                "stdout": process.stdout,
                "stderr": process.stderr,
            }
        )
        if process.returncode == 0 and tmp_output.exists():
            payload = load_json(tmp_output)
            if payload.get("boards"):
                output.parent.mkdir(parents=True, exist_ok=True)
                tmp_output.replace(output)
                result.update({"status": "passed", "provider": payload.get("provider"), "board_count": len(payload.get("boards") or [])})
                return result
            result.update({"status": "failed", "error": "empty board list"})
        else:
            result.update({"status": "failed", "error": f"fetch exited {process.returncode}"})
    except subprocess.TimeoutExpired as exc:
        result.update(
            {
                "status": "timeout",
                "duration_sec": round(time.time() - started, 3),
                "error": f"fetch timed out after {timeout_sec}s",
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
            }
        )
    finally:
        if tmp_output.exists():
            tmp_output.unlink()
    return result


def cache_fresh(path: Path, max_age_hours: float) -> bool:
    if not path.exists():
        return False
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    return age_hours <= max_age_hours


def board_to_metric(board: dict[str, Any], kind: str, provider: str) -> dict[str, Any]:
    pct_change = float(board.get("pct_change") or 0)
    turnover = float(board.get("turnover") or 0)
    company_count = float(board.get("company_count") or 0)
    leader_pct = float(board.get("leading_stock_pct_change") or 0)
    breadth = 0.55 if pct_change > 0 else 0.4 if pct_change < 0 else 0.5
    overheat = 0.8 if pct_change >= 6 or leader_pct >= 15 else 0.5 if pct_change >= 3 else 0.2
    turnover_score = min(max(turnover / 1_000_000_000, -1), 1)
    return {
        "name": board.get("name"),
        "kind": kind,
        "relative_strength_5d": pct_change,
        "relative_strength": pct_change,
        "turnover_change_5d": turnover_score,
        "turnover_heat": turnover,
        "breadth": breadth,
        "policy_industry_catalyst": False,
        "capital_flow_score": 0,
        "capital_flow": 0,
        "overheat_score": overheat,
        "evidence_window": "realtime_snapshot",
        "data_time": now_iso(),
        "status_reason": f"{provider} {kind} board snapshot: pct_change={pct_change}, leader={board.get('leading_stock')}",
        "source_refs": [
            {
                "source_name": provider,
                "board_code": board.get("board_code"),
                "leading_stock": board.get("leading_stock"),
                "leading_stock_code": board.get("leading_stock_code"),
                "company_count": company_count,
            }
        ],
    }


def build_metrics(board_payloads: list[dict[str, Any]], output: Path, limit_per_kind: int) -> dict[str, Any]:
    sectors: list[dict[str, Any]] = []
    for payload in board_payloads:
        provider = payload.get("provider") or "unknown"
        kind = payload.get("kind") or "unknown"
        for board in (payload.get("boards") or [])[:limit_per_kind]:
            if board.get("name"):
                sectors.append(board_to_metric(board, kind, provider))
    metrics = {
        "as_of": datetime.now().date().isoformat(),
        "generated_at": now_iso(),
        "benchmark": "沪深300",
        "sectors": sectors,
    }
    write_json(output, metrics)
    return metrics


def run_generate_state(metrics_path: Path, state_output: Path, timeout_sec: int) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/generate_sector_state.py",
        "--input",
        str(metrics_path),
        "--output",
        str(state_output),
        "--generated-by",
        "bounded_sector_refresh",
    ]
    started = time.time()
    try:
        process = subprocess.run(  # noqa: S603 - static repo-local command
            command,
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
            check=False,
        )
        return {
            "status": "passed" if process.returncode == 0 else "failed",
            "exit_code": process.returncode,
            "duration_sec": round(time.time() - started, 3),
            "stdout": process.stdout,
            "stderr": process.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "duration_sec": round(time.time() - started, 3),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "error": f"generate_sector_state timed out after {timeout_sec}s",
        }


def state_fresh(path: Path, max_age_hours: float) -> bool:
    if not path.exists():
        return False
    try:
        payload = load_json(path)
        generated_at = payload.get("generated_at")
        if generated_at:
            generated = datetime.fromisoformat(str(generated_at))
            return datetime.now().astimezone() - generated <= timedelta(hours=max_age_hours)
    except Exception:  # noqa: BLE001
        pass
    return cache_fresh(path, max_age_hours)


def render_summary(report: dict[str, Any]) -> str:
    lines = [
        f"板块状态刷新：{report['status']}",
        f"生成时间：{report['generated_at']}",
        f"耗时：{report['duration_sec']}s",
        f"状态文件：{report.get('state_output')}",
        "",
        "数据源结果：",
    ]
    for item in report.get("fetch_results", []):
        lines.append(
            f"- {item.get('kind')}: {item.get('status')} provider={item.get('provider')} boards={item.get('board_count')} duration={item.get('duration_sec')}s"
        )
        if item.get("fallback"):
            lines.append(f"  fallback={item.get('fallback')}")
        if item.get("error"):
            lines.append(f"  error={item.get('error')}")
    if report.get("warnings"):
        lines.append("")
        lines.append("降级/提醒：")
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh sector state with bounded runtime and cache fallback")
    parser.add_argument("--boards-dir", default="runtime/market-data")
    parser.add_argument("--metrics-output", default="runtime/sector-metrics.latest.json")
    parser.add_argument("--state-output", default="runtime/sector-state.latest.json")
    parser.add_argument("--health-output", default="runtime/sector-refresh.latest.json")
    parser.add_argument("--summary-output", default="runtime/sector-refresh.latest.txt")
    parser.add_argument("--lock-file", default="runtime/locks/sector-refresh.lock")
    parser.add_argument("--fetch-timeout-sec", type=int, default=45)
    parser.add_argument("--generate-timeout-sec", type=int, default=20)
    parser.add_argument("--lock-stale-sec", type=int, default=900)
    parser.add_argument("--cache-max-age-hours", type=float, default=24)
    parser.add_argument("--state-max-age-hours", type=float, default=24)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--metric-limit-per-kind", type=int, default=30)
    args = parser.parse_args()

    started = time.time()
    lock_path = ROOT_DIR / args.lock_file
    boards_dir = ROOT_DIR / args.boards_dir
    metrics_output = ROOT_DIR / args.metrics_output
    state_output = ROOT_DIR / args.state_output
    health_output = ROOT_DIR / args.health_output
    summary_output = ROOT_DIR / args.summary_output
    warnings: list[str] = []
    fetch_results: list[dict[str, Any]] = []
    board_payloads: list[dict[str, Any]] = []

    try:
        acquire_lock(lock_path, args.lock_stale_sec)
    except RuntimeError as exc:
        report = {
            "generated_at": now_iso(),
            "status": "skipped_locked",
            "duration_sec": round(time.time() - started, 3),
            "warnings": [str(exc)],
            "fetch_results": [],
            "state_output": str(state_output),
        }
        write_json(health_output, report)
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(render_summary(report), encoding="utf-8")
        print(render_summary(report), end="")
        return 0

    try:
        for kind in ["concept", "industry"]:
            board_output = boards_dir / f"sector-boards.{kind}.latest.json"
            result = run_fetch(kind, args.limit, args.fetch_timeout_sec, board_output)
            if result.get("status") == "passed":
                board_payloads.append(load_json(board_output))
                fetch_results.append(result)
                continue

            if cache_fresh(board_output, args.cache_max_age_hours):
                cached = load_json(board_output)
                board_payloads.append(cached)
                result["fallback"] = "cached_board_snapshot"
                result["cached_provider"] = cached.get("provider")
                result["cached_board_count"] = len(cached.get("boards") or [])
                warnings.append(f"{kind} fetch failed; used cached board snapshot")
            else:
                warnings.append(f"{kind} fetch failed and no fresh cache is available")
            fetch_results.append(result)

        generated_state = False
        generate_result: dict[str, Any] | None = None
        if board_payloads:
            metrics = build_metrics(board_payloads, metrics_output, args.metric_limit_per_kind)
            if metrics.get("sectors"):
                generate_result = run_generate_state(metrics_output, state_output, args.generate_timeout_sec)
                generated_state = generate_result.get("status") == "passed"
                if not generated_state:
                    warnings.append("generate_sector_state failed")
            else:
                warnings.append("board payloads produced no sector metrics")
        else:
            warnings.append("no board payloads available")

        if generated_state:
            status = "passed" if not any(item.get("fallback") for item in fetch_results) else "degraded"
        elif state_fresh(state_output, args.state_max_age_hours):
            status = "degraded_stale_state"
            warnings.append("kept existing fresh sector-state because refresh did not produce a new state")
        else:
            status = "failed"

        report = {
            "generated_at": now_iso(),
            "status": status,
            "duration_sec": round(time.time() - started, 3),
            "state_output": str(state_output),
            "metrics_output": str(metrics_output),
            "warnings": warnings,
            "fetch_results": fetch_results,
            "generate_result": generate_result,
        }
        write_json(health_output, report)
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(render_summary(report), encoding="utf-8")
        print(render_summary(report), end="")
        return 0 if status in {"passed", "degraded", "degraded_stale_state"} else 2
    finally:
        if lock_path.exists():
            lock_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
