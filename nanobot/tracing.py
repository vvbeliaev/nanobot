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
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nanobot.agent.hook import AgentHook

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


class TracingHook(AgentHook):
    """AgentHook that writes trace events when NANOBOT_TRACE=1.

    Designed for use with CompositeHook:
        hook = CompositeHook(_LoopHook(), TracingHook(session_id, model))

    Args:
        session_id: identifier written to every record, e.g. "telegram:12345"
        model: model name written to llm_call records
        llm_event: event name for LLM calls (default "llm_call")
        tool_event: event name for tool calls (default "tool_call")
        workspace: optional workspace path; when provided writes traces to
            {workspace}/.traces/{safe_session_id}_{date}.jsonl
    """

    def __init__(
        self,
        session_id: str,
        model: str,
        llm_event: str = "llm_call",
        tool_event: str = "tool_call",
        workspace: Path | None = None,
    ) -> None:
        self._session_id = session_id
        self._model = model
        self._llm_event = llm_event
        self._tool_event = tool_event
        self._workspace = workspace

    def _get_path(self) -> Path | None:
        if self._workspace is not None:
            safe_session_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", self._session_id)
            date_str = datetime.now().strftime("%Y-%m-%d")
            traces_dir = self._workspace / ".traces"
            traces_dir.mkdir(parents=True, exist_ok=True)
            return traces_dir / f"{safe_session_id}_{date_str}.jsonl"
        return _resolve_path()

    def _write(self, event: str, **fields: Any) -> None:
        """Append one JSON record to the trace file. Never raises."""
        path = self._get_path()
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
            self._write(
                self._tool_event,
                session_id=self._session_id,
                tool=tc.name,
                args_preview=args_str[:200],
                iteration=context.iteration,
            )

    async def after_iteration(self, context: Any) -> None:
        if not enabled():
            return
        reasoning_preview: str | None = None
        if context.response is not None:
            rc = getattr(context.response, "reasoning_content", None)
            if rc:
                reasoning_preview = rc[:500]
        self._write(
            self._llm_event,
            session_id=self._session_id,
            model=self._model,
            iteration=context.iteration,
            prompt_tokens=context.usage.get("prompt_tokens", 0),
            completion_tokens=context.usage.get("completion_tokens", 0),
            has_tool_calls=bool(context.tool_calls),
            stop_reason=context.stop_reason,
            **({"reasoning_preview": reasoning_preview} if reasoning_preview is not None else {}),
        )

    def finalize_content(self, context: Any, content: Any) -> Any:
        return content

    async def before_run(self, channel: str, chat_id: str, workspace: Path) -> None:
        if not enabled():
            return
        self._write(
            "run_start",
            session_id=self._session_id,
            channel=channel,
            model=self._model,
        )

    async def after_run(self, channel: str, chat_id: str, workspace: Path, stop_reason: str) -> None:
        if not enabled():
            return
        self._write(
            "run_end",
            session_id=self._session_id,
            stop_reason=stop_reason,
        )
