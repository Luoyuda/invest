#!/usr/bin/env python3
"""Replay recommendation outcomes with later prices and sector statuses."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_prices(path: str) -> dict[str, float]:
    prices = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                prices[row["code"]] = float(row["price"])
            except (KeyError, ValueError):
                continue
    return prices


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay recommendation outcomes")
    parser.add_argument("--run", default="runtime/recommendation-runs/latest.json")
    parser.add_argument("--prices-csv", required=True, help="CSV columns: code,price")
    parser.add_argument("--output", "-o", default="runtime/replay.latest.json")
    args = parser.parse_args()

    run = load_json(args.run)
    prices = load_prices(args.prices_csv)
    rows = []
    for rec in run.get("recommendations", []):
        code = rec.get("code")
        start = (rec.get("price_reference") or {}).get("value")
        latest = prices.get(code)
        change_pct = None
        if start and latest is not None:
            change_pct = round((latest - float(start)) / float(start) * 100, 2)
        rows.append(
            {
                "code": code,
                "name": rec.get("name"),
                "sector": rec.get("sector"),
                "sector_status": rec.get("sector_status"),
                "start_price": start,
                "latest_price": latest,
                "change_pct": change_pct,
                "invalid_if": rec.get("invalid_if", []),
                "review_hint": "check_invalid_if_and_sector_strength",
            }
        )

    payload = {
        "run_id": run.get("run_id"),
        "generated_at": datetime.now().astimezone().isoformat(),
        "outcomes": rows,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Outcomes: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
