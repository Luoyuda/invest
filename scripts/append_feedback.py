#!/usr/bin/env python3
"""Append user feedback or validation failures to runtime/feedback-log.jsonl."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Append feedback to feedback-log.jsonl")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--feedback-type", default="user_feedback")
    parser.add_argument("--failure-type", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--affected-stock", default="")
    parser.add_argument("--affected-sector", default="")
    parser.add_argument("--action-needed", default="review")
    parser.add_argument("--output", "-o", default="runtime/feedback-log.jsonl")
    args = parser.parse_args()

    record = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "run_id": args.run_id,
        "feedback_type": args.feedback_type,
        "failure_type": args.failure_type,
        "summary": args.summary,
        "affected_stock": args.affected_stock,
        "affected_sector": args.affected_sector,
        "action_needed": args.action_needed,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Appended feedback to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
