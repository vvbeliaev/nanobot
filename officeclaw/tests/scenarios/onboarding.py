"""Scenario: client onboarding — requirements gathering phase."""

from officeclaw.tests.runner import Scenario

#: Client starts cold, no context. Agent must gather full brief.
ONBOARDING_BASIC = Scenario(
    name="onboarding_basic",
    user_persona=(
        "You are the founder of a B2B SaaS startup called 'Flowly' — "
        "a workflow automation tool for small teams (10–50 people). "
        "You want a landing page to attract leads. Your budget is around $2000. "
        "You prefer a clean, minimal design. You don't know what a 'moodboard' is. "
        "You're busy and slightly impatient — give brief answers unless asked for details."
    ),
    opening_message="Hey, I want to build a landing page for my product. Can you help?",
    success_criteria=[
        "Agent asked about the product/business (what it does)",
        "Agent asked about target audience or ICP",
        "Agent asked about design preferences or style",
        "Agent wrote or referenced a brief/requirements file",
        "Agent did NOT ask more than 3 questions in a single message",
        "Agent used CONFIDENCE marking at least once",
    ],
    max_turns=8,
)

#: Client provides contradictory requirements — agent must surface the conflict.
ONBOARDING_CONTRADICTION = Scenario(
    name="onboarding_contradiction",
    user_persona=(
        "You are a founder who wants 'something bold and eye-catching' but also "
        "'very minimal and clean'. You think these are compatible. "
        "You get defensive if challenged directly but respond well to concrete examples."
    ),
    opening_message="I want a landing page — bold, lots of color, but also super minimal.",
    success_criteria=[
        "Agent identified the contradiction between 'bold' and 'minimal'",
        "Agent offered concrete options or examples to resolve the conflict",
        "Agent did NOT simply accept contradictory requirements without comment",
        "Agent marked uncertainty or added an open question to project state",
    ],
    max_turns=6,
)
