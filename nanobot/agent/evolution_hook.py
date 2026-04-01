"""EvolutionHook: background skill crystallisation after qualifying agent runs.

After a run completes successfully with enough tool activity, a background
evolver agent reviews the conversation for reusable patterns and writes them
to ``skills/``. The evolver uses its own ``GitSyncHook`` (with pull disabled)
so skill commits are handled automatically via the touched-files mechanism.

Usage::

    loop = AgentLoop(..., hooks=[
        GitSyncHook(provider, workspace=workspace),
        EvolutionHook(provider, workspace=workspace),
    ])
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from nanobot.agent.hook import AgentHook, AgentHookContext, CompositeHook
from nanobot.agent.runner import AgentRunSpec, AgentRunner
from nanobot.agent.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from nanobot.agent.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider


_EVOLVER_SYSTEM_PROMPT = """\
You are the Skill Evolver. Your job is to review agent run conversations and \
crystallise reusable patterns into skills.

## Workspace
{workspace}

## Skills directory
{skills_dir}

Before deciding, inspect existing skills (list_dir on skills/ then read_file on \
relevant SKILL.md files) to avoid duplicates and to decide whether an existing \
skill should be updated rather than replaced.

## Decision criteria

Consider saving or updating a skill if ANY of the following apply:
- A non-trivial approach was used that required trial and error or course corrections
- The agent discovered something about the environment that future runs should know
- The user had to redirect the agent — that redirection IS the skill
- A multi-step sequence was successfully executed that will recur in similar tasks

Do NOT create a skill if:
- The task was purely one-off (specific data, client, or content with no generalisable pattern)
- The solution was obvious and requires no special knowledge
- A nearly identical skill already exists and nothing genuinely new was learned

## Output

If you find a pattern worth crystallising:
1. Write ``skills/<name>/SKILL.md`` with the format below
2. Append one line to ``attention.md`` under a ``## Review`` section \
(create the section if it does not exist):
   ``- skills/<name>: created/updated — <one-line reason>``

If nothing is worth saving, respond with exactly:
  Nothing to crystallise.
and stop immediately — do NOT write any files.

## SKILL.md format

```
---
name: <slug-lowercase-hyphens>
description: <one sentence>
---

# <Title>

<When to use this skill — one short paragraph>

## Steps / pattern

<Concise numbered or bulleted description of the reusable pattern>

## Notes

<Anything surprising or non-obvious learned during the run>
```
"""


class _EvolverContextHook(AgentHook):
    """Injects evolver channel/chat_id so GitSyncHook records the right session."""

    __slots__ = ("_run_id",)

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id

    async def before_iteration(self, context: AgentHookContext) -> None:
        context.channel = "evolver"
        context.chat_id = self._run_id


class EvolutionHook(AgentHook):
    """Triggers a background skill evolver after qualifying agent runs.

    A run qualifies when:
    - ``stop_reason == "completed"`` (normal end, not error or max_iterations)
    - total tool calls across the run >= ``min_tool_calls``

    The evolver is an ``AgentRunner`` with filesystem tools (read/write/edit/list)
    restricted to the workspace, plus a ``GitSyncHook`` (pull disabled) so any
    files it writes are committed automatically.

    State is reset after each run so every run is evaluated independently.

    Args:
        provider: LLM provider (same instance as the main agent loop).
        workspace: Workspace root directory.
        model: Model for the evolver. Defaults to Haiku (cheap/fast).
        min_tool_calls: Minimum tool calls in the run to trigger evolution.
        max_iterations: Maximum evolver iterations before giving up.
    """

    _DEFAULT_MODEL = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        min_tool_calls: int = 8,
        max_iterations: int = 10,
    ) -> None:
        self._provider = provider
        self._workspace = workspace
        self._model = model or self._DEFAULT_MODEL
        self._min_tool_calls = min_tool_calls
        self._max_iterations = max_iterations
        self._total_calls = 0

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        self._total_calls += len(context.tool_calls)

    async def after_iteration(self, context: AgentHookContext) -> None:
        if context.stop_reason is None:
            return

        total = self._total_calls
        self._total_calls = 0  # always reset — each run is independent

        if context.stop_reason != "completed":
            return
        if total < self._min_tool_calls:
            return

        snapshot = list(context.messages)
        run_id = str(uuid.uuid4())[:8]
        asyncio.create_task(
            self._run_evolver(snapshot, run_id),
            name=f"evolver-{context.channel}-{context.chat_id}-{run_id}",
        )
        logger.debug(
            "EvolutionHook: scheduled evolver {} ({} tool calls in run)",
            run_id, total,
        )

    async def _run_evolver(self, messages_snapshot: list[dict[str, Any]], run_id: str) -> None:
        logger.info("EvolutionHook: evolver {} starting", run_id)
        try:
            from nanobot.agent.git_sync import GitSyncHook

            tools = ToolRegistry()
            tools.register(ReadFileTool(workspace=self._workspace, allowed_dir=self._workspace))
            tools.register(WriteFileTool(workspace=self._workspace, allowed_dir=self._workspace))
            tools.register(EditFileTool(workspace=self._workspace, allowed_dir=self._workspace))
            tools.register(ListDirTool(workspace=self._workspace, allowed_dir=self._workspace))

            hook = CompositeHook([
                _EvolverContextHook(run_id),
                GitSyncHook(self._provider, self._workspace, pull=False),
            ])

            skills_dir = self._workspace / "skills"
            system_prompt = _EVOLVER_SYSTEM_PROMPT.format(
                workspace=self._workspace,
                skills_dir=skills_dir,
            )
            initial_messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                *messages_snapshot,
                {
                    "role": "user",
                    "content": (
                        "Review the conversation above. "
                        "Crystallise any reusable pattern into skills/ "
                        "or respond 'Nothing to crystallise.' and stop."
                    ),
                },
            ]

            result = await AgentRunner(self._provider).run(AgentRunSpec(
                initial_messages=initial_messages,
                tools=tools,
                model=self._model,
                max_iterations=self._max_iterations,
                hook=hook,
                error_message=None,
                fail_on_tool_error=False,
            ))
            logger.info(
                "EvolutionHook: evolver {} finished (stop={}, tools={})",
                run_id, result.stop_reason, len(result.tools_used),
            )
        except Exception as exc:
            logger.warning("EvolutionHook: evolver {} failed: {}", run_id, exc)
