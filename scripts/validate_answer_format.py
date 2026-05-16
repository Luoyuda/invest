#!/usr/bin/env python3
"""Validate final Markdown answer formatting before sending to IM."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def strip_fenced_code(text: str) -> str:
    return re.sub(r"```[\s\S]*?```", "", text)


def is_markdown_table_separator(line: str) -> bool:
    stripped = line.strip()
    if "|" not in stripped:
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if len(cells) < 2:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def is_table_like_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.count("|") >= 2


def count_markdown_tables(text: str) -> int:
    lines = strip_fenced_code(text).splitlines()
    table_blocks = 0
    in_table = False
    for idx, line in enumerate(lines):
        previous_line = lines[idx - 1] if idx > 0 else ""
        next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
        starts_table = is_markdown_table_separator(line) and is_table_like_line(previous_line)
        continues_table = in_table and is_table_like_line(line)

        if starts_table:
            table_blocks += 1
            in_table = True
            continue
        if continues_table:
            continue

        if in_table and not is_table_like_line(next_line):
            in_table = False
        elif in_table and not is_table_like_line(line):
            in_table = False
    return table_blocks


def count_html_tables(text: str) -> int:
    text_without_code = strip_fenced_code(text)
    return len(re.findall(r"<table\b", text_without_code, flags=re.IGNORECASE))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate final answer format for IM delivery")
    parser.add_argument("answer_file", help="Markdown answer file")
    parser.add_argument("--max-tables", type=int, default=5)
    parser.add_argument("--json-output", default="")
    args = parser.parse_args()

    path = Path(args.answer_file)
    if not path.exists():
        print(f"ERROR: missing answer file: {path}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    markdown_tables = count_markdown_tables(text)
    html_tables = count_html_tables(text)
    table_count = markdown_tables + html_tables
    errors = []
    if table_count > args.max_tables:
        errors.append(f"answer has {table_count} tables, exceeds max {args.max_tables}")

    payload = {
        "answer_file": str(path),
        "status": "passed" if not errors else "failed",
        "max_tables": args.max_tables,
        "table_count": table_count,
        "markdown_tables": markdown_tables,
        "html_tables": html_tables,
        "errors": errors,
    }
    if args.json_output:
        output = Path(args.json_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if errors:
        print("Answer format validation failed:")
        for error in errors:
            print(f"- {error}")
        return 2

    print("Answer format validation passed")
    print(f"Tables: {table_count}/{args.max_tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
