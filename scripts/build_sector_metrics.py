#!/usr/bin/env python3
"""Build sector metrics input for generate_sector_state.py.

V1 accepts a simple CSV so data can come from AKShare, Eastmoney exports,
manual tables, or future providers without changing downstream scripts.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build sector metrics JSON from CSV")
    parser.add_argument("--csv", required=True, help="CSV with sector metrics")
    parser.add_argument("--output", "-o", default="runtime/sector-metrics.latest.json")
    parser.add_argument("--benchmark", default="沪深300")
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    with Path(args.csv).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row.get("name") or row.get("sector")
            if not name:
                continue
            rows.append(
                {
                    "name": name,
                    "relative_strength_5d": to_float(row.get("relative_strength_5d")),
                    "turnover_change_5d": to_float(row.get("turnover_change_5d")),
                    "breadth": to_float(row.get("breadth")),
                    "policy_industry_catalyst": row.get("policy_industry_catalyst", ""),
                    "capital_flow_score": to_float(row.get("capital_flow_score")),
                    "overheat_score": to_float(row.get("overheat_score")),
                    "source_refs": [row.get("source", "csv")],
                    "data_time": row.get("data_time") or datetime.now().astimezone().isoformat(),
                }
            )

    payload = {
        "as_of": datetime.now().date().isoformat(),
        "benchmark": args.benchmark,
        "sectors": rows,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Sectors: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
