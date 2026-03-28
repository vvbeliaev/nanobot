"""Local JSONL trace writer for session analysis.

Activated via NANOBOT_TRACE=1 environment variable.
Writes to ~/.nanobot/logs/trace_YYYY-MM-DD.jsonl (one file per day).

Each line is a JSON record with at minimum {"event": "...", "ts": "..."}.

Event types:
  llm_call        — one LLM request/response in the main agent loop
  tool_call       — a tool execution (name, args preview, result size)
  subagent_start  — a sub-agent was spawned
  subagent_llm_call — one LLM request inside a sub-agent loop
  subagent_end    — sub-agent finished (ok or error)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_trace_path: Path | None = None
_initialized = False


def _resolve_path() -> Path | None:
    global _trace_path, _initialized
    if _initialized:
        return _trace_path
    _initialized = True
    if not os.getenv("NANOBOT_TRACE"):
        return None
    from nanobot.config.paths import get_logs_dir
    date_str = datetime.now().strftime("%Y-%m-%d")
    _trace_path = get_logs_dir() / f"trace_{date_str}.jsonl"
    return _trace_path


def enabled() -> bool:
    return bool(os.getenv("NANOBOT_TRACE"))


def write(event: str, **fields: Any) -> None:
    """Append one JSON record to today's trace file. Never raises."""
    path = _resolve_path()
    if path is None:
        return
    record: dict[str, Any] = {
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        **fields,
    }
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass  # tracing must never break the main flow
