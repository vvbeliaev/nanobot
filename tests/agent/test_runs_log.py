"""Unit tests for RunsLogHook."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from nanobot.agent.hook import AgentHookContext
from nanobot.agent.runs_log import RunsLogHook
from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class _DummyProvider(LLMProvider):
    """Provider stub that returns a canned summary string."""

    def __init__(self, summary: str = "[agent/channel] test: ok\n\nStatus: complete") -> None:
        super().__init__()
        self._summary = summary
        self.calls = 0

    async def chat(self, *args, **kwargs) -> LLMResponse:
        self.calls += 1
        return LLMResponse(content=self._summary, tool_calls=[])

    def get_default_model(self) -> str:
        return "test-model"


class _FailingProvider(_DummyProvider):
    async def chat(self, *args, **kwargs) -> LLMResponse:
        raise RuntimeError("provider down")


def _ctx(
    iteration: int,
    *,
    stop_reason: str | None = None,
    tool_calls: list[ToolCallRequest] | None = None,
    channel: str = "cli",
    chat_id: str = "direct",
) -> AgentHookContext:
    return AgentHookContext(
        iteration=iteration,
        messages=[],
        tool_calls=tool_calls or [],
        stop_reason=stop_reason,
        channel=channel,
        chat_id=chat_id,
    )


def _read_records(workspace: Path, channel: str = "cli", chat_id: str = "direct") -> list[dict]:
    safe = f"{channel}_{chat_id}"
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = workspace / ".runs" / f"{safe}_{date_str}.jsonl"
    assert path.exists(), f"expected runs log at {path}"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


@pytest.mark.asyncio
async def test_writes_record_with_llm_summary(tmp_path: Path) -> None:
    provider = _DummyProvider("[agent/channel] phase: did the thing")
    hook = RunsLogHook(provider, workspace=tmp_path)

    await hook.before_iteration(_ctx(0))
    await hook.before_execute_tools(
        _ctx(
            0,
            tool_calls=[
                ToolCallRequest(id="1", name="write_file", arguments={"path": "notes.md"}),
                ToolCallRequest(id="2", name="shell", arguments={"cmd": "ls"}),
            ],
        )
    )
    await hook.after_iteration(_ctx(0, stop_reason="complete"))

    records = _read_records(tmp_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["schema_version"] == 1
    assert rec["session_id"] == "cli:direct"
    assert rec["stop_reason"] == "complete"
    assert rec["touched_files"] == ["notes.md"]
    assert rec["tool_counts"] == {"write_file": 1, "shell": 1}
    assert rec["summary"] == "[agent/channel] phase: did the thing"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_skips_non_final_iterations(tmp_path: Path) -> None:
    hook = RunsLogHook(_DummyProvider(), workspace=tmp_path)

    await hook.before_iteration(_ctx(0))
    await hook.after_iteration(_ctx(0, stop_reason=None))  # not final, no record

    assert not (tmp_path / ".runs").exists()


@pytest.mark.asyncio
async def test_fallback_summary_when_llm_fails(tmp_path: Path) -> None:
    hook = RunsLogHook(_FailingProvider(), workspace=tmp_path)

    await hook.before_iteration(_ctx(0))
    await hook.after_iteration(_ctx(0, stop_reason="blocked"))

    records = _read_records(tmp_path)
    assert len(records) == 1
    summary = records[0]["summary"]
    assert "[agent/channel] auto: run complete" in summary
    assert "Status: blocked" in summary


@pytest.mark.asyncio
async def test_state_resets_between_runs(tmp_path: Path) -> None:
    """Mutable state must clear after each completed run."""
    hook = RunsLogHook(_DummyProvider(), workspace=tmp_path)

    # Run 1
    await hook.before_iteration(_ctx(0))
    await hook.before_execute_tools(
        _ctx(
            0,
            tool_calls=[
                ToolCallRequest(id="1", name="write_file", arguments={"path": "a.md"})
            ],
        )
    )
    await hook.after_iteration(_ctx(0, stop_reason="complete"))

    # Run 2 — different files, must not see Run 1's state
    await hook.before_iteration(_ctx(0))
    await hook.before_execute_tools(
        _ctx(
            0,
            tool_calls=[
                ToolCallRequest(id="2", name="edit_file", arguments={"path": "b.md"})
            ],
        )
    )
    await hook.after_iteration(_ctx(0, stop_reason="complete"))

    records = _read_records(tmp_path)
    assert len(records) == 2
    assert records[0]["touched_files"] == ["a.md"]
    assert records[1]["touched_files"] == ["b.md"]
    assert records[0]["tool_counts"] == {"write_file": 1}
    assert records[1]["tool_counts"] == {"edit_file": 1}


@pytest.mark.asyncio
async def test_cron_channel_marks_trigger(tmp_path: Path) -> None:
    hook = RunsLogHook(_DummyProvider(), workspace=tmp_path)

    await hook.before_iteration(_ctx(0, channel="cron", chat_id="job1"))
    await hook.after_iteration(
        _ctx(0, stop_reason="complete", channel="cron", chat_id="job1")
    )

    records = _read_records(tmp_path, channel="cron", chat_id="job1")
    assert records[0]["trigger"] == "cron"
    assert records[0]["channel"] == "cron"
