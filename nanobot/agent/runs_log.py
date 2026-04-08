"""RunsLogHook: per-run LLM-summarised observability log written to workspace/.runs/.

Mirrors the spirit of GitSyncHook (LLM describes what the agent did) but is
git-independent: instead of creating a commit, the hook appends one JSON
record to ``{workspace}/.runs/{session_id}_{date}.jsonl``, parallel to the
trace files produced by ``TracingHook``.

Each record is a structured snapshot of one completed run:
  - timestamps, channel/chat_id, stop_reason, error
  - which workspace files the agent wrote/edited (via write_file/edit_file)
  - tool-call counts
  - an LLM-generated free-text summary describing what happened

If the LLM call fails for any reason, a structured fallback summary is used.
All errors are logged and swallowed — this hook must never break a run.

Usage::

    loop = AgentLoop(..., hooks=[RunsLogHook(provider, workspace=workspace)])
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from nanobot.agent.hook import AgentHook, AgentHookContext

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider

_WRITE_TOOLS = frozenset({"write_file", "edit_file"})

_SCHEMA_VERSION = 1


class RunsLogHook(AgentHook):
    """Lifecycle hook that writes one LLM-summarised record per completed run.

    Parallel to ``TracingHook`` (which writes fine-grained per-event records),
    this hook writes exactly one record per finished run with a human-readable
    summary of what the agent actually did. It does NOT touch git.

    Args:
        provider: The same LLMProvider used by the agent loop.
        workspace: Workspace directory; records land under ``{workspace}/.runs/``.
        model: Model for summary generation. Defaults to Haiku (fast/cheap).
    """

    _DEFAULT_MODEL = "claude-haiku-4-5-20251001"
    _MAX_TRACE_TOOL_CALLS = 20
    _MAX_SUMMARY_TOKENS = 256

    def __init__(
        self,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
    ) -> None:
        self._provider = provider
        self._workspace = workspace
        self._model = model or self._DEFAULT_MODEL
        self._touched_files: set[str] = set()
        self._tool_names: list[str] = []
        self._started_at: str | None = None

    async def before_iteration(self, context: AgentHookContext) -> None:
        """Capture run start timestamp on the first iteration only."""
        if context.iteration == 0 and self._started_at is None:
            self._started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        """Track tool usage and which workspace files were written this run."""
        for tc in context.tool_calls:
            self._tool_names.append(tc.name)
            if tc.name in _WRITE_TOOLS and "path" in tc.arguments:
                self._touched_files.add(tc.arguments["path"])

    async def after_iteration(self, context: AgentHookContext) -> None:
        """On the final iteration, write a single LLM-summarised run record."""
        if context.stop_reason is None:
            return
        try:
            started_at = self._started_at or datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )
            ended_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            touched = sorted(self._touched_files)
            tool_counts = _count_tools(self._tool_names)
            trace_context = _read_trace_tools(
                self._workspace,
                context.channel,
                context.chat_id,
                self._MAX_TRACE_TOOL_CALLS,
            )
            trigger = "cron" if context.channel == "cron" else "channel"
            summary = await self._generate_summary(
                trigger, context.stop_reason, touched, trace_context
            )
            record: dict[str, Any] = {
                "schema_version": _SCHEMA_VERSION,
                "session_id": f"{context.channel}:{context.chat_id}",
                "channel": context.channel,
                "chat_id": context.chat_id,
                "started_at": started_at,
                "ended_at": ended_at,
                "stop_reason": context.stop_reason,
                "trigger": trigger,
                "iterations": context.iteration + 1,
                "touched_files": touched,
                "tool_counts": tool_counts,
                "summary": summary,
            }
            if context.error:
                record["error"] = context.error
            self._write_record(context.channel, context.chat_id, record)
        except Exception as exc:
            logger.warning("RunsLogHook.after_iteration: {}", exc)
        finally:
            self._touched_files.clear()
            self._tool_names.clear()
            self._started_at = None

    def _write_record(self, channel: str, chat_id: str, record: dict[str, Any]) -> None:
        """Append one JSON record to today's per-session JSONL file."""
        safe_session_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", f"{channel}:{chat_id}")
        date_str = datetime.now().strftime("%Y-%m-%d")
        runs_dir = self._workspace / ".runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        path = runs_dir / f"{safe_session_id}_{date_str}.jsonl"
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(line)

    async def _generate_summary(
        self,
        trigger: str,
        stop_reason: str,
        touched: list[str],
        trace_context: str,
    ) -> str:
        """Ask the LLM to write a structured run summary."""
        tools_section = (
            f"\nTools used during run:\n{trace_context}" if trace_context else ""
        )
        if touched:
            files_section = "\nFiles written/edited during run:\n" + "\n".join(
                f"- {p}" for p in touched
            )
        else:
            files_section = "\nNo files were written during this run."
        prompt = (
            "You summarise agent runs into a short observability record.\n"
            "Write ONLY the summary body — no preamble, no markdown fences.\n\n"
            f"Trigger: {trigger}\n"
            f"Stop reason: {stop_reason}"
            f"{tools_section}"
            f"{files_section}\n\n"
            "Format (follow exactly):\n"
            f"[agent/{trigger}] <phase>: <one-line summary>\n\n"
            "Status: <complete|ready-for-review|blocked>\n"
            "Uncertainty: <what was unclear, or 'none'>\n"
            "General summary: <2-4 sentences on what happened in the run>"
        )
        try:
            response = await self._provider.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self._model,
                max_tokens=self._MAX_SUMMARY_TOKENS,
                temperature=0.3,
            )
            msg = (response.content or "").strip()
            if msg:
                return msg
        except Exception as exc:
            logger.warning("RunsLogHook: summary LLM call failed: {}", exc)

        return (
            f"[agent/{trigger}] auto: run complete\n\n"
            f"Status: {stop_reason}\n"
            f"Uncertainty: none\n"
            f"General summary: run finished with stop_reason={stop_reason}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_tools(names: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for n in names:
        counts[n] = counts.get(n, 0) + 1
    return counts


def _read_trace_tools(workspace: Path, channel: str, chat_id: str, limit: int) -> str:
    """Read recent tool_call events from today's trace file for this session."""
    try:
        session_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", f"{channel}:{chat_id}")
        date_str = datetime.now().strftime("%Y-%m-%d")
        trace_path = workspace / ".traces" / f"{session_id}_{date_str}.jsonl"
        if not trace_path.exists():
            return ""
        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        calls: list[str] = []
        for line in lines:
            try:
                rec = json.loads(line)
                if rec.get("event") == "tool_call":
                    preview = rec.get("args", "")[:60]
                    calls.append(f"- {rec['tool']}({preview})")
            except Exception:
                pass
        return "\n".join(calls[-limit:])
    except Exception:
        return ""
