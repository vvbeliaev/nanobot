"""Scenario test runner for nanobot agents.

Uses Haiku as a user simulator and Sonnet as an LLM judge.
Requires no external infrastructure — runs entirely in-process via AgentLoop.process_direct().

Usage::

    asyncio.run(main())

    async def main():
        from nanobot.providers.registry import create_provider
        from nanobot.agent.loop import AgentLoop
        from nanobot.bus.queue import MessageBus

        provider = create_provider("anthropic/claude-haiku-4-5-20251001")
        agent = AgentLoop(bus=MessageBus(), provider=provider, workspace=Path("digital-agency"))

        runner = ScenarioRunner(agent=agent, provider=provider)
        result = await runner.run(SCENARIO)
        result.print_summary()
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nanobot.agent.loop import AgentLoop
    from nanobot.providers.base import LLMProvider


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    """A single test scenario definition."""
    name: str
    user_persona: str          # Who Haiku is playing
    opening_message: str       # First message the user sends
    success_criteria: list[str]  # What the agent must do/say to pass
    max_turns: int = 10
    channel: str = "telegram"
    chat_id: str = "test_user"


@dataclass
class Turn:
    role: str   # "user" | "agent"
    content: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


@dataclass
class CriterionResult:
    criterion: str
    passed: bool
    reason: str


@dataclass
class JudgeVerdict:
    passed: bool
    score: int            # 0–10
    reasoning: str
    criteria: list[CriterionResult] = field(default_factory=list)


@dataclass
class ScenarioResult:
    scenario_name: str
    turns: list[Turn]
    verdict: JudgeVerdict

    def print_summary(self) -> None:
        status = "PASSED" if self.verdict.passed else "FAILED"
        print(f"\n{'='*60}")
        print(f"Scenario: {self.scenario_name}  [{status}]  Score: {self.verdict.score}/10")
        print(f"Turns: {len(self.turns)}")
        print(f"\nCriteria:")
        for c in self.verdict.criteria:
            mark = "✓" if c.passed else "✗"
            print(f"  {mark} {c.criterion}")
            print(f"    → {c.reason}")
        print(f"\nJudge reasoning:\n{self.verdict.reasoning}")
        print("="*60)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

USER_SIMULATOR_SYSTEM = """\
You are playing the role of a user in a test conversation with an AI assistant.

Character:
{persona}

Rules:
- Stay in character throughout.
- Be concise (1–3 sentences per message).
- If your goal is achieved or the conversation has reached a natural pause
  that requires waiting, reply with exactly: DONE
- Do not add meta-commentary, just respond as the character would.
"""

JUDGE_PROMPT = """\
Evaluate this agent conversation against the success criteria below.
Be strict: PASS only if the criterion is clearly met in the transcript.

SCENARIO: {scenario_name}
USER PERSONA: {persona}

SUCCESS CRITERIA:
{criteria}

TRANSCRIPT:
{transcript}

Respond in this exact format:

CRITERION_RESULTS:
- <criterion text>: PASS|FAIL — <one-line reason>

SCORE: <integer 0-10>
VERDICT: PASSED|FAILED
REASONING: <2-4 sentences overall assessment>
"""


class ScenarioRunner:
    """Runs scenario tests against a live AgentLoop.

    Args:
        agent: An initialised AgentLoop (git_sync should be disabled for tests).
        provider: LLM provider used for both the user simulator and the judge.
        user_model: Model for the user simulator (Haiku recommended).
        judge_model: Model for the judge (Sonnet recommended).
        logs_dir: Directory to write JSONL logs. Created if absent.
    """

    USER_MODEL = "claude-haiku-4-5-20251001"
    JUDGE_MODEL = "claude-sonnet-4-6"

    def __init__(
        self,
        agent: AgentLoop,
        provider: LLMProvider,
        user_model: str | None = None,
        judge_model: str | None = None,
        logs_dir: Path = Path("tests/logs"),
    ) -> None:
        self.agent = agent
        self.provider = provider
        self.user_model = user_model or self.USER_MODEL
        self.judge_model = judge_model or self.JUDGE_MODEL
        self.logs_dir = logs_dir

    async def run(self, scenario: Scenario) -> ScenarioResult:
        """Run a scenario end-to-end and return the result."""
        turns: list[Turn] = []

        # Turn 0: fixed opening message from user
        turns.append(Turn(role="user", content=scenario.opening_message))

        for _ in range(scenario.max_turns):
            # Agent responds to the last user turn
            agent_content = await self._agent_respond(scenario, turns[-1].content)
            turns.append(Turn(role="agent", content=agent_content))

            # Haiku generates the next user message (or signals DONE)
            user_next = await self._user_next(scenario, turns)
            if user_next is None:
                break
            turns.append(Turn(role="user", content=user_next))

        verdict = await self._judge(scenario, turns)
        result = ScenarioResult(scenario_name=scenario.name, turns=turns, verdict=verdict)
        self._write_log(result)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _agent_respond(self, scenario: Scenario, user_content: str) -> str:
        response = await self.agent.process_direct(
            content=user_content,
            session_key=f"scenario:{scenario.name}",
            channel=scenario.channel,
            chat_id=scenario.chat_id,
        )
        return (response.content if response else "") or "[no response]"

    async def _user_next(self, scenario: Scenario, turns: list[Turn]) -> str | None:
        """Ask Haiku to produce the next user message, or return None if done."""
        response = await self.provider.chat(
            messages=[
                {
                    "role": "system",
                    "content": USER_SIMULATOR_SYSTEM.format(persona=scenario.user_persona),
                },
                {
                    "role": "user",
                    "content": (
                        f"Conversation so far:\n{_fmt_transcript(turns)}\n\n"
                        "Your next message:"
                    ),
                },
            ],
            model=self.user_model,
            max_tokens=256,
            temperature=0.7,
        )
        content = (response.content or "").strip()
        return None if content.upper() == "DONE" else content

    async def _judge(self, scenario: Scenario, turns: list[Turn]) -> JudgeVerdict:
        """Call the judge LLM and parse its structured output."""
        criteria_str = "\n".join(f"- {c}" for c in scenario.success_criteria)
        response = await self.provider.chat(
            messages=[{
                "role": "user",
                "content": JUDGE_PROMPT.format(
                    scenario_name=scenario.name,
                    persona=scenario.user_persona,
                    criteria=criteria_str,
                    transcript=_fmt_transcript(turns),
                ),
            }],
            model=self.judge_model,
            max_tokens=800,
            temperature=0.1,
        )
        return _parse_verdict(scenario, response.content or "")

    def _write_log(self, result: ScenarioResult) -> None:
        """Append the result as a JSONL record in logs_dir."""
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d")
            path = self.logs_dir / f"{result.scenario_name}_{ts}.jsonl"
            record = {
                "scenario": result.scenario_name,
                "passed": result.verdict.passed,
                "score": result.verdict.score,
                "turns": len(result.turns),
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "transcript": [asdict(t) for t in result.turns],
                "verdict": asdict(result.verdict),
            }
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass  # logging must never break the test


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_transcript(turns: list[Turn]) -> str:
    lines = []
    for t in turns:
        label = "USER" if t.role == "user" else "AGENT"
        lines.append(f"[{label}] {t.content}")
    return "\n".join(lines)


def _parse_verdict(scenario: Scenario, raw: str) -> JudgeVerdict:
    """Parse judge output into JudgeVerdict. Falls back gracefully on parse errors."""
    criteria: list[CriterionResult] = []

    # Parse per-criterion results
    for line in raw.splitlines():
        m = re.match(r"\s*-\s*(.+?):\s*(PASS|FAIL)\s*[—-]\s*(.+)", line, re.IGNORECASE)
        if m:
            criteria.append(CriterionResult(
                criterion=m.group(1).strip(),
                passed=m.group(2).upper() == "PASS",
                reason=m.group(3).strip(),
            ))

    # If parsing failed, create unknown entries
    if not criteria:
        criteria = [CriterionResult(c, False, "parse error") for c in scenario.success_criteria]

    # Parse score
    score = 0
    sm = re.search(r"SCORE:\s*(\d+)", raw, re.IGNORECASE)
    if sm:
        score = min(10, max(0, int(sm.group(1))))

    # Parse verdict
    passed = bool(re.search(r"VERDICT:\s*PASSED", raw, re.IGNORECASE))

    # Parse reasoning
    reasoning = ""
    rm = re.search(r"REASONING:\s*(.+?)(?:\n\n|\Z)", raw, re.IGNORECASE | re.DOTALL)
    if rm:
        reasoning = rm.group(1).strip()

    return JudgeVerdict(passed=passed, score=score, reasoning=reasoning, criteria=criteria)
