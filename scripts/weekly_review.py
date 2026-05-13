#!/usr/bin/env python3
"""Summarize weekly recommendation failures and run outcomes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"failure_type": "invalid_feedback_record", "summary": line})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate weekly review report")
    parser.add_argument("--runs-dir", default="runtime/recommendation-runs")
    parser.add_argument("--feedback", default="runtime/feedback-log.jsonl")
    parser.add_argument("--output", "-o", default="runtime/weekly-review.latest.json")
    args = parser.parse_args()

    runs_dir = Path(args.runs_dir)
    run_files = sorted(runs_dir.glob("*.json")) if runs_dir.exists() else []
    runs = []
    for file in run_files:
        try:
            runs.append(json.loads(file.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            runs.append({"run_id": file.name, "invalid_json": True})

    feedback = load_jsonl(Path(args.feedback))
    failure_counts = Counter(row.get("failure_type", "unknown") for row in feedback)

    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "runs_count": len(runs),
        "feedback_count": len(feedback),
        "top_failure_types": failure_counts.most_common(),
        "high_risk_items": [
            row
            for row in feedback
            if row.get("failure_type")
            in {"source_mismatch", "extract_error", "price_scope_error", "unsafe_instruction", "low_activity_overrated"}
        ],
        "action_items": [],
    }

    for failure_type, count in failure_counts.most_common():
        if count >= 2 or failure_type in {"unsafe_instruction", "extract_error", "source_mismatch"}:
            report["action_items"].append(
                {
                    "failure_type": failure_type,
                    "count": count,
                    "action": "create_rule_change_proposal",
                }
            )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Runs: {len(runs)}")
    print(f"Feedback: {len(feedback)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
