# Runtime diff proposals — Attention OS на базе nanobot

*Март 2026 | Анализ что нужно менять, а что уже работает*

---

## TL;DR

Для **прототипа (Фаза 0–1)** менять nanobot runtime не нужно.
Всё core-поведение уже есть в дефолтном nanobot.

Для **продакшн-надёжности (Фаза 2+)** — да, нужны изменения рантайма.

---

## Что уже работает из коробки

| Что нужно по спеку | Как покрывается в nanobot | Статус |
|---|---|---|
| Системный промпт агента | `AGENTS.md` в корне workspace читается автоматически | ✅ |
| Identity агента | `SOUL.md` в корне workspace | ✅ |
| Skills система | `workspace/skills/*/SKILL.md` → XML summary в промпте | ✅ |
| Blocking actions (поведение) | AGENTS.md: "жди явного ответа" — prompt-level | ✅ прототип |
| Confidence marking | AGENTS.md правила — prompt-level | ✅ |
| Uncertainty detection | AGENTS.md UNCERTAINTY RULE — prompt-level | ✅ |
| Prompt injection defense | AGENTS.md SECURITY RULE + nanobot context.py:96 уже тегирует untруsted | ✅ |
| Project state (чтение/запись) | read_file / write_file / edit_file — дефолтные инструменты | ✅ |
| Structured phase summary | AGENTS.md инструкция → write_file artifacts/phase_X.yaml | ✅ |
| Telegram уведомления | telegram channel — есть | ✅ |
| Heartbeat / cron | cron service — есть | ✅ |
| Memory consolidation | MemoryConsolidator → MEMORY.md / HISTORY.md | ✅ |
| Spawn subagents | SpawnTool — есть | ✅ |
| max_iterations бюджет | max_iterations=40 в конфиге | ✅ частично |

---

## Структурный gap: workspace layout

claw-os структурирован иначе чем nanobot ожидает.

**nanobot ожидает:**
```
workspace/
├── AGENTS.md          ← bootstrap
├── SOUL.md            ← bootstrap
├── skills/            ← SkillsLoader смотрит сюда
│   └── site_builder/SKILL.md
└── memory/
    └── MEMORY.md
```

**claw-os сейчас:**
```
claw-os/
├── AGENTS.md          ✅ правильно
├── SOUL.md            ✅ правильно
├── global/
│   └── skills/        ← нужно переместить или симлинк
│       └── site_builder.md
└── clients/
```

**Решение для прототипа:** переместить `global/skills/` в `skills/` (nanobot формат),
или добавить в config.json:

```json
{
  "agents": {
    "defaults": {
      "workspace": "/path/to/claw-os"
    }
  }
}
```

nanobot будет читать `AGENTS.md` / `SOUL.md` из корня claw-os автоматически.
Скиллы нужно переложить в `claw-os/skills/site_builder/SKILL.md`.

---

## Что НЕ работает для прототипа (и как обойти)

### 1. triggers.yaml — не читается nanobot

triggers.yaml сейчас — это **документация архитектуры**, не конфиг рантайма.
nanobot его не парсит.

**Для прототипа:** триггеры эмулируются вручную:
- `inbound_message` → просто telegram сообщение от клиента
- `heartbeat` → настроить через nanobot cron в конфиге
- `phase_complete` → агент сам пишет в Telegram что фаза завершена и ждёт

### 2. Per-client workspace isolation — нет в рантайме

Все клиенты в одном workspace. Агент технически может прочитать `clients/acme_corp/` из сессии `clients/techstart/`.

**Для прототипа:** AGENTS.md инструкция ("работай строго в своём контексте") + naming convention. Для одного оператора с двумя клиентами — достаточно.

### 3. Telegram inline keyboards (кнопки да/нет)

nanobot telegram channel шлёт только текст. Кнопок нет.

**Для прототипа:** оператор отвечает текстом ("да", "деплой", "отмена"). Агент интерпретирует по AGENTS.md. Неудобно но работает.

---

## Что менять в рантайме — только для Фазы 2+

Эти изменения нужны когда прототип доказал ценность и нужна надёжность:

### P0 — Multi-context workspace routing

Сессия `telegram:{client_chat_id}` → `clients/{client_id}/` workspace.

```python
# Новый ContextResolver
# AgentLoop создаёт ContextBuilder(workspace=resolver.resolve(channel, chat_id))
```

**Почему не для прототипа:** один клиент → не нужно. Два клиента → ручная изоляция работает.

### P1 — Blocking Actions Guard (код, не промпт)

```python
# ToolRegistry.execute() перехватывает deploy_prod, send_to_client
# → ApprovalQueue → уведомление → resume по ответу оператора
```

**Почему не для прототипа:** prompt-level ("жди ответа") работает для одного оператора который активен. Ломается при масштабировании или долгих сессиях.

### P1 — Telegram inline keyboards

`InlineKeyboardMarkup` + `CallbackQueryHandler` в TelegramChannel.

**Почему не для прототипа:** текстовые ответы достаточны для теста гипотезы.

### P2 — Per-trigger skills scoping

Каждый триггер активирует только разрешённые скиллы.

```python
# ContextBuilder.build_system_prompt(allowed_skills=["site_builder", "moodboard"])
# (параметр УЖЕ есть в сигнатуре, просто не передаётся из triggers)
```

**Почему не для прототипа:** все скиллы в промпте с описаниями — агент сам выбирает нужные.

### P2 — Token/time budget с pause-and-notify

```python
class SessionBudget:
    max_tokens: int = 150_000
    # на exceed → pause + notify operator
```

**Почему не для прототипа:** max_iterations=40 покрывает. Мониторить вручную.

---

## Итоговый план для прототипа

### Что сделать прямо сейчас (без кода)

1. **Переложить скиллы** в nanobot-формат:
   ```
   claw-os/skills/site_builder/SKILL.md
   claw-os/skills/deploy_prod/SKILL.md
   claw-os/skills/moodboard_pinterest/SKILL.md
   claw-os/skills/requirements_gathering/SKILL.md
   claw-os/skills/send_to_client/SKILL.md
   ```

2. **Настроить nanobot** на workspace `claw-os/`:
   ```json
   { "agents": { "defaults": { "workspace": "~/ai/nanobot/claw-os" } } }
   ```

3. **Запустить gateway** с Telegram channel — готово к тесту.

4. **triggers.yaml** оставить как living spec — реализовать постепенно.

### Метрика успеха Фазы 0

После 20 оценок лидов через Telegram → LLM синтезирует ICP паттерн.
Насколько точный? Если точный — hypothesis confirmed, идём в Фазу 1.

---

## Принцип

> Нет смысла строить надёжный рантайм для гипотезы которая не проверена.
> Сначала доказать что поведение правильное → потом сделать его надёжным.

Прометный блокинг в промпте неидеален но **достаточен** чтобы понять
работает ли концепция вообще. Если работает — P1 изменения рантайма окупятся.
