#!/usr/bin/env python3
"""Run a cron task with lock, timeout, retry, and health reporting."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def safe_name(value: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-")
    return name or "task"


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT_DIR / path


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def acquire_lock(lock_path: Path, stale_after_sec: int) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        age = time.time() - lock_path.stat().st_mtime
        if age <= stale_after_sec:
            raise RuntimeError(f"task already running; lock={lock_path}, age_sec={round(age, 1)}")
        lock_path.unlink()
    fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(f"pid={os.getpid()}\ncreated_at={now_iso()}\n")


def truncate_text(value: str | bytes | None, max_chars: int) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + f"\n...<truncated {len(value) - max_chars} chars>"


def stale_success_fresh(path: Path, max_age_hours: float) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        finished_at = payload.get("finished_at") or payload.get("generated_at")
        if finished_at:
            finished = datetime.fromisoformat(str(finished_at))
            return datetime.now().astimezone() - finished <= timedelta(hours=max_age_hours)
    except Exception:  # noqa: BLE001 - stale fallback should also tolerate older marker formats
        pass
    return (time.time() - path.stat().st_mtime) / 3600 <= max_age_hours


def run_once(command: list[str], timeout_sec: int, max_output_chars: int) -> dict[str, Any]:
    started = time.time()
    result: dict[str, Any] = {
        "started_at": now_iso(),
        "timeout_sec": timeout_sec,
    }
    try:
        process = subprocess.run(  # noqa: S603 - command is supplied by the local cron configuration
            command,
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
            check=False,
        )
        result.update(
            {
                "status": "passed" if process.returncode == 0 else "failed",
                "exit_code": process.returncode,
                "duration_sec": round(time.time() - started, 3),
                "stdout": truncate_text(process.stdout, max_output_chars),
                "stderr": truncate_text(process.stderr, max_output_chars),
            }
        )
    except subprocess.TimeoutExpired as exc:
        result.update(
            {
                "status": "timeout",
                "exit_code": None,
                "duration_sec": round(time.time() - started, 3),
                "stdout": truncate_text(exc.stdout, max_output_chars),
                "stderr": truncate_text(exc.stderr, max_output_chars),
                "error": f"task timed out after {timeout_sec}s",
            }
        )
    return result


def render_summary(report: dict[str, Any]) -> str:
    lines = [
        f"任务：{report['name']}",
        f"状态：{report['status']}",
        f"开始：{report['started_at']}",
        f"结束：{report['finished_at']}",
        f"耗时：{report['duration_sec']}s",
        f"命令：{' '.join(report['command'])}",
        "",
        "尝试记录：",
    ]
    for item in report.get("attempts", []):
        lines.append(
            f"- #{item.get('attempt')} {item.get('status')} exit={item.get('exit_code')} duration={item.get('duration_sec')}s"
        )
        if item.get("error"):
            lines.append(f"  error={item.get('error')}")
    if report.get("warnings"):
        lines.append("")
        lines.append("降级/提醒：")
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a cron task with lock, timeout, retry, and health reporting")
    parser.add_argument("--name", required=True, help="Human readable task name")
    parser.add_argument("--timeout-sec", type=int, default=300, help="Timeout for each attempt")
    parser.add_argument("--retries", type=int, default=0, help="Retries after the first failed/timeout attempt")
    parser.add_argument("--retry-delay-sec", type=float, default=5.0)
    parser.add_argument("--lock-file", default="", help="Default: runtime/locks/<name>.lock")
    parser.add_argument("--lock-stale-sec", type=int, default=900)
    parser.add_argument("--health-output", default="", help="Default: runtime/task-runs/<name>.latest.json")
    parser.add_argument("--summary-output", default="", help="Default: runtime/task-runs/<name>.latest.txt")
    parser.add_argument("--success-marker", default="", help="Default: runtime/task-runs/<name>.last-success.json")
    parser.add_argument("--allow-stale-success", action="store_true", help="Exit 0 if the task fails but a recent success marker exists")
    parser.add_argument("--stale-success-max-age-hours", type=float, default=24)
    parser.add_argument("--max-output-chars", type=int, default=6000)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("missing command after --")

    name = safe_name(args.name)
    lock_path = resolve_path(args.lock_file or f"runtime/locks/{name}.lock")
    health_output = resolve_path(args.health_output or f"runtime/task-runs/{name}.latest.json")
    summary_output = resolve_path(args.summary_output or f"runtime/task-runs/{name}.latest.txt")
    success_marker = resolve_path(args.success_marker or f"runtime/task-runs/{name}.last-success.json")

    started = time.time()
    started_at = now_iso()
    warnings: list[str] = []
    attempts: list[dict[str, Any]] = []

    try:
        acquire_lock(lock_path, args.lock_stale_sec)
    except RuntimeError as exc:
        report = {
            "name": args.name,
            "status": "skipped_locked",
            "started_at": started_at,
            "finished_at": now_iso(),
            "duration_sec": round(time.time() - started, 3),
            "command": command,
            "attempts": [],
            "warnings": [str(exc)],
        }
        write_json(health_output, report)
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(render_summary(report), encoding="utf-8")
        print(render_summary(report), end="")
        return 0

    try:
        total_attempts = max(args.retries, 0) + 1
        for index in range(1, total_attempts + 1):
            attempt = run_once(command, args.timeout_sec, args.max_output_chars)
            attempt["attempt"] = index
            attempts.append(attempt)
            if attempt["status"] == "passed":
                break
            if index < total_attempts and args.retry_delay_sec > 0:
                time.sleep(args.retry_delay_sec)

        passed = attempts[-1]["status"] == "passed"
        status = "passed" if passed else attempts[-1]["status"]
        if not passed and args.allow_stale_success and stale_success_fresh(success_marker, args.stale_success_max_age_hours):
            status = "degraded_stale_success"
            warnings.append(f"task failed; using recent success marker {success_marker}")

        report = {
            "name": args.name,
            "status": status,
            "started_at": started_at,
            "finished_at": now_iso(),
            "duration_sec": round(time.time() - started, 3),
            "command": command,
            "timeout_sec": args.timeout_sec,
            "retries": args.retries,
            "attempts": attempts,
            "warnings": warnings,
            "success_marker": str(success_marker),
        }
        write_json(health_output, report)
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(render_summary(report), encoding="utf-8")
        if passed:
            write_json(success_marker, report)
        print(render_summary(report), end="")
        return 0 if status in {"passed", "degraded_stale_success"} else 2
    finally:
        if lock_path.exists():
            lock_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
