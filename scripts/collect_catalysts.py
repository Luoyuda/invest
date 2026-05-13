#!/usr/bin/env python3
"""Collect catalyst records from a CSV into runtime/catalysts.latest.json."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect catalyst records")
    parser.add_argument("--csv", required=True, help="CSV with catalyst records")
    parser.add_argument("--output", "-o", default="runtime/catalysts.latest.json")
    args = parser.parse_args()

    catalysts = []
    with Path(args.csv).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if not row.get("sector") and not row.get("stock"):
                continue
            catalysts.append(
                {
                    "sector": row.get("sector", ""),
                    "stock": row.get("stock", ""),
                    "type": row.get("type", "policy_industry"),
                    "fact": row.get("fact", ""),
                    "source_name": row.get("source_name", ""),
                    "url": row.get("url", ""),
                    "published_at": row.get("published_at", ""),
                    "impact_chain": row.get("impact_chain", ""),
                    "risk": row.get("risk", ""),
                }
            )

    payload = {"generated_at": datetime.now().astimezone().isoformat(), "catalysts": catalysts}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Catalysts: {len(catalysts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
