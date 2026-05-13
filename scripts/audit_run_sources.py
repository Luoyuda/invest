#!/usr/bin/env python3
"""Audit recommendation run evidence links and value mappings.

This is a lightweight deterministic audit. It checks URL reachability where
possible and verifies that recommendations only reference declared evidence.
It does not claim semantic support; unresolved semantic checks should be
handled by human/LLM review.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


def check_url(url: str, timeout: int = 8) -> tuple[bool, str]:
    if not url or url == "https://...":
        return False, "missing_url"
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 lobster-invest/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 400, f"status_{response.status}"
    except urllib.error.HTTPError as exc:
        if exc.code == 405:
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 lobster-invest/1.0"})
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return 200 <= response.status < 400, f"status_{response.status}"
            except Exception as inner:  # noqa: BLE001
                return False, str(inner)
        return False, f"http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit recommendation run sources")
    parser.add_argument("run_file", nargs="?", default="runtime/recommendation-runs/latest.json")
    parser.add_argument("--output", "-o", default="runtime/source-audit.latest.json")
    parser.add_argument("--skip-network", action="store_true")
    args = parser.parse_args()

    run = json.loads(Path(args.run_file).read_text(encoding="utf-8"))
    evidence = run.get("evidence", [])
    evidence_by_id = {item.get("id"): item for item in evidence}
    errors: list[str] = []
    warnings: list[str] = []
    source_checks: list[dict[str, Any]] = []

    for item in evidence:
        evidence_id = item.get("id")
        for key in ["raw_value", "normalized_value", "unit", "data_time", "source_name", "supports"]:
            if item.get(key) in (None, "", []):
                errors.append(f"evidence {evidence_id} missing {key}")
        if not args.skip_network:
            ok, detail = check_url(str(item.get("url", "")))
            source_checks.append({"id": evidence_id, "url": item.get("url"), "reachable": ok, "detail": detail})
            if not ok:
                warnings.append(f"evidence {evidence_id} url not reachable: {detail}")

    for idx, rec in enumerate(run.get("recommendations", [])):
        for evidence_id in rec.get("evidence_ids", []):
            if evidence_id not in evidence_by_id:
                errors.append(f"recommendations[{idx}] missing evidence {evidence_id}")
        price = rec.get("price_reference") or {}
        evidence_id = price.get("evidence_id")
        if evidence_id and evidence_id not in evidence_by_id:
            errors.append(f"recommendations[{idx}] price evidence missing {evidence_id}")

    report = {
        "run_id": run.get("run_id"),
        "checked_at": datetime.now().astimezone().isoformat(),
        "status": "failed" if errors else "passed",
        "errors": errors,
        "warnings": warnings,
        "source_checks": source_checks,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Status: {report['status']}")
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
