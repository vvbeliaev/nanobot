# humanize — Design Spec

**Date:** 2026-04-03  
**Status:** Draft  
**Goal:** A standalone Python package that makes any LLM runtime communicate like a real human in a messenger.

---

## Problem

LLM responses are instant, uniform, and structurally perfect. Real humans have availability rhythms, typing speed, message fragmentation patterns, and stylistic noise. The moment a bot replies in 200ms with a well-formatted paragraph, the illusion is broken. This package models the communication behavior of a human persona at the runtime level — not as a text transformation, but as a time-aware delivery engine.

**Target:** maintain the illusion convincingly across multiple days, not just a single conversation.

---

## Scope

`humanize` is a **transport-agnostic Python package**. It sits between an LLM call and a messaging channel. It has no opinion about which LLM, which channel, or which bot framework is used. Integration with nanobot (or anything else) is a thin adapter.

Streaming is explicitly **out of scope**: humans send complete messages, not character deltas. The LLM is called without streaming; the human-like effect is achieved through timed delivery of complete message chunks.

---

## Core Model: s(t)

The persona has an internal state `s(t)` — a function of time primarily. States split into two categories:

- **Clock-driven** (`ASLEEP`, `DROWSY`, `BUSY`, `AVAILABLE`): set by `CircadianClock` based on schedule + calendar
- **Conversation-driven** (`ENGAGED`, `DISTRACTED`): transient overrides triggered by conversation activity; they layer on top of the clock baseline and expire after inactivity

Conversational context can perturb the state locally, but the clock baseline always recovers.

### States

```
ASLEEP → DROWSY → AVAILABLE ↔ ENGAGED
                ↕
              BUSY ↔ DISTRACTED
```

| State | Meaning |
|---|---|
| `ASLEEP` | Persona is offline. Messages are queued, not answered. |
| `DROWSY` | Morning or late night. Slow, typo-prone, short messages. |
| `BUSY` | Work hours or calendar event. Delayed, minimal responses. |
| `AVAILABLE` | Free time. Normal response latency and style. |
| `ENGAGED` | Active back-and-forth. Fast replies, more splitting. |
| `DISTRACTED` | Mid-conversation delay spike. Realistic gap. |

### State → Behavior Parameters

| State | read_delay | respond? | typing_speed | typo_rate | split |
|---|---|---|---|---|---|
| ASLEEP | ∞ | defer | — | — | — |
| DROWSY | 30–120s | yes | −40% | ×2 | minimal |
| BUSY | 5–30 min | yes | +20% | low | 1–2 msgs |
| AVAILABLE | 10–60s | yes | normal | normal | full |
| ENGAGED | 2–10s | yes | +20% | low | aggressive |
| DISTRACTED | 2–20 min | yes | normal | medium | minimal |

---

## Architecture

### Data Flow

```
Incoming messages (from conversation partner)
        ↓
  MessageAccumulator
  (sliding window ~3–5s: batches rapid messages into one LLM call)
        ↓
  CircadianClock → s(t)
        ↓
  StateFilter
  ├── ASLEEP → DeferredEvent(respond_at=next_wake_time) → DeferQueue
  └── otherwise ↓
  ResponseScheduler
  (compute delay: f(state, message_length, time_since_last_message))
        ↓
  StatePromptInjector
  (injects state-appropriate few-shot examples into system prompt —
   NOT structured output; LLM writes natural text in the right style)
        ↓
  LLM call (no streaming)
        ↓
  ── deterministic pipeline ──
  MessageSplitter     → split by punctuation + semantic heuristics
  StyleTransformer    → typos, casing, abbreviations, emoji (params from state)
  TimingCalculator    → typing_duration + inter-message pauses per chunk
        ↓
  Iterator[Event]
        ↓
  Transport adapter (nanobot / generic / anything)
```

### Event Types

```python
@dataclass
class TypingStartEvent:
    duration: float           # seconds to show "typing..." indicator

@dataclass
class MessageEvent:
    text: str
    delay_before: float       # pause before sending this chunk

@dataclass
class DeferredEvent:
    respond_at: datetime      # when the persona wakes up and will answer
```

The transport adapter consumes this iterator and handles the actual channel operations (send typing action, sleep, send message, queue deferred).

---

## Package Structure

```
humanize/
├── core/
│   ├── state.py          # PersonaState enum + transition rules
│   ├── clock.py          # CircadianClock: time → state, with jitter
│   ├── persona.py        # PersonaConfig: load from YAML/dict
│   └── events.py         # TypingStartEvent, MessageEvent, DeferredEvent
├── pipeline/
│   ├── accumulator.py    # MessageAccumulator: batch rapid inbound messages
│   ├── scheduler.py      # ResponseScheduler: compute when to start responding
│   ├── injector.py       # StatePromptInjector: few-shot system prompt shaping
│   ├── splitter.py       # MessageSplitter: heuristic text chunking
│   ├── style.py          # StyleTransformer: typos, casing, emoji
│   └── timing.py         # TimingCalculator: duration per chunk
├── adapters/
│   ├── base.py           # Transport ABC: send_typing(), send_message()
│   ├── nanobot.py        # Nanobot integration (~50 lines)
│   └── generic.py        # Minimal reference implementation
└── persistence/
    └── state_store.py    # Persist clock state between process restarts
```

---

## Key Components

### CircadianClock

Configurable 24h profile with stochastic jitter on transitions. Persisted between restarts so the persona's state survives a process restart.

```yaml
persona:
  name: "Alex"
  timezone: "Europe/Moscow"

  schedule:
    sleep:   { from: "23:30", to: "08:00" }
    morning: { from: "08:00", to: "09:30", state: DROWSY }
    work:    { from: "09:30", to: "18:00", state: BUSY }
    evening: { from: "18:00", to: "23:30", state: AVAILABLE }

  calendar:
    - { weekday: "monday", from: "14:00", to: "16:00", state: BUSY }
    - { weekday: "friday", from: "17:00", to: "18:00", state: AVAILABLE }

  jitter_minutes: 20   # gaussian noise on transition times

  style:
    typo_rate: 0.03          # base rate; scaled by state
    max_chunk_length: 120    # chars per message chunk
    emoji_frequency: 0.15    # fraction of messages that get an emoji
    abbreviations: true

  timing:
    typing_speed_cps: 4.5    # chars per second, base
    typing_jitter: 0.25      # ± fraction
    inter_chunk_pause: { min: 0.8, max: 3.5 }
```

Jitter is critical: exact schedule transitions immediately reveal automation.

### MessageAccumulator

Sliding-window buffer on the inbound side. If the conversation partner sends 3 messages in 4 seconds, they are batched and sent to the LLM as a single multi-part request. The LLM responds to all of them at once — this mirrors how a real person reads a pile of messages and replies in one flow.

### StatePromptInjector

Adds a state-specific block to the system prompt with few-shot examples. Does **not** use structured output or XML tags — that shifts responsibility for splitting to the LLM, which is unreliable. Instead, it shapes the *style* of LLM output so the downstream splitter has better material to work with.

Example injection for `BUSY`:
```
You are Alex. Right now you're in the middle of work.
Keep responses short and to the point — 1 or 2 thoughts at most.
No long explanations. You can come back to things later.
Example response style: "yeah ok" / "can we talk later?" / "sounds good, lmk"
```

### MessageSplitter

Deterministic heuristic pipeline (no LLM call):
1. Split on sentence boundaries (`.`, `!`, `?`, `…`)
2. Further split on clause boundaries (`,`, `—`, conjunctions) if chunk > `max_chunk_length`
3. Merge fragments shorter than a minimum threshold
4. Respect state: `BUSY` and `DROWSY` collapse to 1–2 chunks regardless

### StyleTransformer

Keyboard-layout-aware typo model. Random character substitution is immediately obvious as fake — real typos cluster around adjacent keys, common phonetic substitutions, and missing spaces after punctuation. Parameters (rates) are drawn from the state config.

### DeferQueue

When `ASLEEP`: incoming messages are persisted to a queue with the original timestamp. When the clock transitions to `DROWSY` or `AVAILABLE`, the queue is drained: the persona "wakes up," reads the accumulated messages, and responds to them in one contextually-aware batch.

---

## Nanobot Integration

The only change to nanobot is in `_dispatch` in [loop.py](../../nanobot/agent/loop.py). Instead of directly calling `bus.publish_outbound(response)`, the response passes through a `HumanizeDelivery` object:

```python
# nanobot/humanize.py  (~50 lines, no changes to existing files)
class HumanizeDelivery:
    def __init__(self, pipeline: ResponsePipeline, transport: NanobotTransport): ...
    async def deliver(self, response: OutboundMessage, state: PersonaState) -> None:
        async for event in self.pipeline.process(response.content, state):
            await self.transport.handle(event)
```

`NanobotTransport` implements `Transport` ABC using `bus.publish_outbound` for messages and channel-specific typing actions.

No changes to `AgentRunner`, `AgentHook`, providers, or any channel code.

---

## Implementation Order (by complexity)

| Phase | Components | Notes |
|---|---|---|
| 1 | `CircadianClock`, `StateStore`, `PersonaConfig` | Pure datetime, no external deps |
| 2 | `MessageAccumulator`, `ResponseScheduler`, `TimingCalculator` | asyncio + math |
| 3 | `MessageSplitter`, basic `StyleTransformer` | String processing |
| 4 | `StatePromptInjector` + few-shot examples | Needs prompt engineering |
| 5 | `DeferQueue` (ASLEEP scenario) | Persistence |
| 6 | `NanobotAdapter` | Integration |
| 7 | Keyboard-layout typo model | Quality enhancement |

---

## Out of Scope (v1)

- Learning individual conversation partner style
- Fine-tuned LLM for style transfer
- Structured LLM output (`<message>` tags) for splitting
- LLM streaming
- Multi-persona routing (different personas per chat)
- Read receipts simulation
