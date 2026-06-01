#!/usr/bin/env python3
"""Fallback wrapper for Tonghuashun iFinD MCP calls through mcporter.

Agent-facing skills should use the installed iFinD skill first. This wrapper is
for CLI, cron, and gaps not covered by the skill, while still staying inside the
licensed iFinD data boundary.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = "~/.openclaw/mcporter.json"
IFIND_SOURCE = {
    "source_name": "同花顺 iFinD MCP",
    "source_type": "licensed_market_data",
    "stability_tier": "S2",
    "url": "https://mcp.51ifind.com/#/docs/skill-solution",
    "limitations": "优先使用已安装的 iFinD skill；CLI/定时任务或 skill 未覆盖能力才使用 mcporter MCP 兜底。需本机安装 mcporter 并配置 iFinD MCP 授权；禁止降级到未授权网页抓取源。",
}


def config_path(value: str | None = None) -> Path:
    configured = value or os.environ.get("IFIND_MCP_CONFIG") or DEFAULT_CONFIG
    return Path(configured).expanduser()


def require_runtime(config: Path) -> None:
    if shutil.which("mcporter") is None:
        raise RuntimeError("mcporter is not installed; install it and configure iFinD MCP before running data fetchers")
    if not config.exists():
        raise RuntimeError(f"iFinD MCP config not found: {config}")


def parse_stdout(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for start in ("{", "["):
        index = text.find(start)
        if index >= 0:
            try:
                return json.loads(text[index:])
            except json.JSONDecodeError:
                continue
    return text


def call_ifind(tool: str, query: str, timeout: float = 30.0, config: str | None = None) -> dict[str, Any]:
    cfg = config_path(config)
    require_runtime(cfg)
    command = ["mcporter", "--config", str(cfg), "call", tool, f"query:{query}"]
    started = datetime.now().astimezone()
    process = subprocess.run(  # noqa: S603 - mcporter is the configured local MCP client
        command,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if process.returncode != 0:
        stderr = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(f"iFinD MCP call failed for {tool}: {stderr}")
    return {
        "tool": tool,
        "query": query,
        "data": parse_stdout(process.stdout),
        "stdout": process.stdout.strip(),
        "stderr": process.stderr.strip(),
        "source": {**IFIND_SOURCE, "accessed_at": started.isoformat()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Call Tonghuashun iFinD MCP through mcporter")
    parser.add_argument("tool", help="MCP tool, e.g. hexin-ifind-stock.get_stock_summary")
    parser.add_argument("query", help="Natural-language iFinD query")
    parser.add_argument("--config", default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", "-o", default="")
    args = parser.parse_args()

    payload = call_ifind(args.tool, args.query, timeout=args.timeout, config=args.config)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
