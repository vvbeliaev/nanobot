"""Local JSONL trace writer for session analysis.

Activated via NANOBOT_TRACE=1 environment variable.
Writes to ~/.nanobot/logs/trace_YYYY-MM-DD.jsonl (one file per day).

Each line is a JSON record with at minimum {"event": "...", "ts": "..."}.

Event types:
  llm_call        — one LLM request/response in the main agent loop
  tool_call       — a tool execution (name, args preview)
  subagent_start  — a sub-agent was spawned
  subagent_llm_call — one LLM request inside a sub-agent loop
  subagent_tool_call — a tool execution inside a sub-agent
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


class TracingHook:
    """AgentHook that writes trace events when NANOBOT_TRACE=1.

    Designed for use with CompositeHook:
        hook = CompositeHook(_LoopHook(), TracingHook(session_id, model))

    Args:
        session_id: identifier written to every record, e.g. "telegram:12345"
        model: model name written to llm_call records
        llm_event: event name for LLM calls (default "llm_call")
        tool_event: event name for tool calls (default "tool_call")
    """

    def __init__(
        self,
        session_id: str,
        model: str,
        llm_event: str = "llm_call",
        tool_event: str = "tool_call",
    ) -> None:
        self._session_id = session_id
        self._model = model
        self._llm_event = llm_event
        self._tool_event = tool_event

    def wants_streaming(self) -> bool:
        return False

    async def before_iteration(self, context: Any) -> None:
        pass

    async def on_stream(self, context: Any, delta: str) -> None:
        pass

    async def on_stream_end(self, context: Any, *, resuming: bool) -> None:
        pass

    async def before_execute_tools(self, context: Any) -> None:
        if not enabled():
            return
        for tc in context.tool_calls:
            args_str = json.dumps(tc.arguments, ensure_ascii=False)
            write(
                self._tool_event,
                session_id=self._session_id,
                tool=tc.name,
                args_preview=args_str[:200],
                iteration=context.iteration,
            )

    async def after_iteration(self, context: Any) -> None:
        if not enabled():
            return
        write(
            self._llm_event,
            session_id=self._session_id,
            model=self._model,
            iteration=context.iteration,
            prompt_tokens=context.usage.get("prompt_tokens", 0),
            completion_tokens=context.usage.get("completion_tokens", 0),
            has_tool_calls=bool(context.tool_calls),
            stop_reason=context.stop_reason,
        )

    def finalize_content(self, context: Any, content: Any) -> Any:
        return content
