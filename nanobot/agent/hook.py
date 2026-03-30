"""Shared lifecycle hook primitives for agent runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nanobot.providers.base import LLMResponse, ToolCallRequest


@dataclass(slots=True)
class AgentHookContext:
    """Mutable per-iteration state exposed to runner hooks."""

    iteration: int
    messages: list[dict[str, Any]]
    response: LLMResponse | None = None
    usage: dict[str, int] = field(default_factory=dict)
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    tool_results: list[Any] = field(default_factory=list)
    tool_events: list[dict[str, str]] = field(default_factory=list)
    final_content: str | None = None
    stop_reason: str | None = None
    error: str | None = None


class AgentHook:
    """Minimal lifecycle surface for shared runner customization."""

    def wants_streaming(self) -> bool:
        return False

    async def before_iteration(self, context: AgentHookContext) -> None:
        pass

    async def on_stream(self, context: AgentHookContext, delta: str) -> None:
        pass

    async def on_stream_end(self, context: AgentHookContext, *, resuming: bool) -> None:
        pass

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        pass

    async def after_iteration(self, context: AgentHookContext) -> None:
        pass

    def finalize_content(self, context: AgentHookContext, content: str | None) -> str | None:
        return content

    async def before_run(self, channel: str, chat_id: str, workspace: Path) -> None:
        pass

    async def after_run(self, channel: str, chat_id: str, workspace: Path, stop_reason: str) -> None:
        pass


class CompositeHook(AgentHook):
    """Delegates lifecycle calls to multiple hooks in order."""

    def __init__(self, *hooks: AgentHook) -> None:
        self._hooks = hooks

    def wants_streaming(self) -> bool:
        return any(h.wants_streaming() for h in self._hooks)

    async def before_iteration(self, context: AgentHookContext) -> None:
        for h in self._hooks:
            await h.before_iteration(context)

    async def on_stream(self, context: AgentHookContext, delta: str) -> None:
        for h in self._hooks:
            await h.on_stream(context, delta)

    async def on_stream_end(self, context: AgentHookContext, *, resuming: bool) -> None:
        for h in self._hooks:
            await h.on_stream_end(context, resuming=resuming)

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        for h in self._hooks:
            await h.before_execute_tools(context)

    async def after_iteration(self, context: AgentHookContext) -> None:
        for h in self._hooks:
            await h.after_iteration(context)

    def finalize_content(self, context: AgentHookContext, content: str | None) -> str | None:
        for h in self._hooks:
            content = h.finalize_content(context, content)
        return content

    async def before_run(self, channel: str, chat_id: str, workspace: Path) -> None:
        for h in self._hooks:
            await h.before_run(channel, chat_id, workspace)

    async def after_run(self, channel: str, chat_id: str, workspace: Path, stop_reason: str) -> None:
        for h in self._hooks:
            await h.after_run(channel, chat_id, workspace, stop_reason)
