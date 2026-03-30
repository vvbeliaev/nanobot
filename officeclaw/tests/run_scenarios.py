"""Run scenario tests against the digital-agency agent.

Usage:
    cd /path/to/nanobot
    python -m officeclaw.tests.run_scenarios
    python -m officeclaw.tests.run_scenarios --scenario onboarding_basic
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.providers.registry import create_provider


WORKSPACE = Path(__file__).parent.parent / "digital-agency"
LOGS_DIR = Path(__file__).parent / "logs"


async def main(scenario_name: str | None = None) -> None:
    from officeclaw.tests.runner import ScenarioRunner
    from officeclaw.tests.scenarios.onboarding import ONBOARDING_BASIC, ONBOARDING_CONTRADICTION

    all_scenarios = {
        "onboarding_basic": ONBOARDING_BASIC,
        "onboarding_contradiction": ONBOARDING_CONTRADICTION,
    }

    to_run = (
        [all_scenarios[scenario_name]]
        if scenario_name
        else list(all_scenarios.values())
    )

    # Provider — uses same API key as normal nanobot
    model = os.environ.get("NANOBOT_TEST_MODEL", "anthropic/claude-opus-4-5")
    provider = create_provider(model)

    # AgentLoop — git_sync intentionally OFF for tests
    agent = AgentLoop(
        bus=MessageBus(),
        provider=provider,
        workspace=WORKSPACE,
        model=model,
        max_iterations=20,
    )

    runner = ScenarioRunner(
        agent=agent,
        provider=provider,
        logs_dir=LOGS_DIR,
    )

    results = []
    for scenario in to_run:
        print(f"\nRunning: {scenario.name} ...")
        result = await runner.run(scenario)
        result.print_summary()
        results.append(result)

    # Summary
    passed = sum(1 for r in results if r.verdict.passed)
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{len(results)} passed")
    print(f"Logs: {LOGS_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="Run a single scenario by name")
    args = parser.parse_args()
    asyncio.run(main(args.scenario))
