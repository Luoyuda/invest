#!/usr/bin/env python3
"""Write a validated outbound message artifact without sending it."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]


def now_stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-")
    return slug or "message"


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT_DIR / path


def validate_format(message_path: Path, max_tables: int) -> dict[str, Any]:
    process = subprocess.run(  # noqa: S603 - static repo-local validator
        [
            sys.executable,
            "scripts/validate_answer_format.py",
            str(message_path),
            "--max-tables",
            str(max_tables),
        ],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "status": "passed" if process.returncode == 0 else "failed",
        "exit_code": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a validated outbound message artifact")
    parser.add_argument("--input", "-i", required=True, help="Markdown message to enqueue")
    parser.add_argument("--task", required=True)
    parser.add_argument("--channel", default="im")
    parser.add_argument("--outbox-dir", default="runtime/outbox/pending")
    parser.add_argument("--max-tables", type=int, default=5)
    args = parser.parse_args()

    source = resolve_path(args.input)
    if not source.exists():
        raise SystemExit(f"message file not found: {source}")

    outbox_dir = resolve_path(args.outbox_dir)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    message_id = f"{now_stamp()}-{safe_slug(args.task)}"
    message_path = outbox_dir / f"{message_id}.md"
    meta_path = outbox_dir / f"{message_id}.json"
    message = source.read_text(encoding="utf-8")
    message_path.write_text(message, encoding="utf-8")

    validation = validate_format(message_path, args.max_tables)
    metadata = {
        "id": message_id,
        "created_at": datetime.now().astimezone().isoformat(),
        "task": args.task,
        "channel": args.channel,
        "message_path": str(message_path),
        "source_path": str(source),
        "status": "pending" if validation["status"] == "passed" else "blocked_invalid_format",
        "validation": validation,
    }
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0 if validation["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
