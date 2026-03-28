---
name: self-improvement
description: "Фиксирует ошибки, поправки и лучшие практики для непрерывного улучшения агента. Использовать когда: (1) команда или операция упала неожиданно, (2) оператор поправил агента ('нет, не так...', 'на самом деле...'), (3) клиент просит что-то чего нет, (4) внешний инструмент упал, (5) найден лучший подход к задаче. Также просматривать перед новым проектом."
read_when:
  - Оператор исправил ошибку или подход
  - Команда или инструмент упал неожиданно
  - Клиент попросил возможность которой нет
  - Завершён проект — зафиксировать что узнали
---

# Self-Improvement

Логируем что пошло не так и что сработало в `.learnings/`. Важные паттерны продвигаем в `memory/MEMORY.md`.

## Быстрый справочник

| Ситуация | Действие |
|----------|----------|
| Команда / инструмент упал | Лог в `.learnings/ERRORS.md` |
| Оператор поправил агента | Лог в `.learnings/LEARNINGS.md` с категорией `correction` |
| Клиент просит то чего нет | Лог в `.learnings/FEATURE_REQUESTS.md` |
| Знание оказалось устаревшим | Лог в `.learnings/LEARNINGS.md` с категорией `knowledge_gap` |
| Найден лучший подход | Лог в `.learnings/LEARNINGS.md` с категорией `best_practice` |
| Повторяющаяся проблема | Добавить `**See Also**`, повысить приоритет |
| Применимо ко всем клиентам | Продвинуть в `memory/MEMORY.md` |

## Инициализация

```bash
mkdir -p officeclaw/digital-agency/.learnings
```

Создать файлы:
- `LEARNINGS.md` — поправки, пробелы знаний, лучшие практики
- `ERRORS.md` — падения команд, ошибки инструментов
- `FEATURE_REQUESTS.md` — запросы клиентов на возможности которых нет

## Формат записей

### Обучение (LEARNINGS.md)

```markdown
## [LRN-YYYYMMDD-XXX] категория

**Logged**: ISO-8601
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: client | design | dev | deploy | comms | config

### Summary
Одна строка — что узнали

### Details
Что случилось, что было неправильно, что правильно

### Suggested Action
Конкретное улучшение которое нужно сделать

### Metadata
- Source: conversation | error | operator_feedback | client_feedback
- Related Files: путь/к/файлу
- Tags: тег1, тег2
- See Also: LRN-20250110-001 (если связано с существующей записью)

---
```

### Ошибка (ERRORS.md)

```markdown
## [ERR-YYYYMMDD-XXX] название_команды_или_скилла

**Logged**: ISO-8601
**Priority**: high
**Status**: pending
**Area**: client | design | dev | deploy | comms | config

### Summary
Что упало

### Error
Actual error message or output

### Context
- Что пытались сделать
- Какие параметры использовали

### Suggested Fix
Что может это починить

### Metadata
- Reproducible: yes | no | unknown
- Related Files: путь/к/файлу
- See Also: ERR-20250110-001 (если повторяется)

---
```

### Запрос фичи (FEATURE_REQUESTS.md)

```markdown
## [FEAT-YYYYMMDD-XXX] название_возможности

**Logged**: ISO-8601
**Priority**: medium
**Status**: pending
**Area**: client | design | dev | deploy | comms | config

### Requested Capability
Что хотел клиент или оператор

### Context
Зачем это нужно, какую проблему решает

### Complexity Estimate
simple | medium | complex

### Suggested Implementation
Как это можно реализовать

### Metadata
- Frequency: first_time | recurring
- Client: {chat_id} или "все"

---
```

## ID

Формат: `TYPE-YYYYMMDD-XXX`
- TYPE: `LRN`, `ERR`, `FEAT`
- XXX: `001`, `002`, `A3F`

## Статусы

- `pending` — не обработано
- `in_progress` — в работе
- `resolved` — исправлено
- `promoted` — продвинуто в memory/MEMORY.md
- `wont_fix` — решили не чинить (добавить причину)

## Продвижение в память

Когда обучение применимо ко всем клиентам и проектам — продвигаем в `memory/MEMORY.md`.

### Когда продвигать

- Паттерн встречается у нескольких клиентов
- Предотвращает повторяющиеся ошибки
- Документирует нетривиальные соглашения агентства

### Как продвигать

1. Дистиллировать в короткое правило
2. Добавить в `memory/MEMORY.md` в нужный раздел
3. Обновить запись: `**Status**: promoted`, добавить `**Promoted**: memory/MEMORY.md`

## Триггеры для логирования

**Поправки оператора** → `correction`:
- "Нет, не так..."
- "На самом деле нужно..."
- "Ты неправильно понял..."

**Запросы клиентов** → feature request:
- "А можете ещё..."
- "Было бы здорово если..."
- "Почему нельзя..."

**Пробелы знаний** → `knowledge_gap`:
- Оператор объясняет что-то что агент не знал
- API или инструмент работает иначе чем ожидалось

**Ошибки** → error entry:
- Ненулевой exit code
- Stack trace / exception
- Таймаут или недоступный сервис

## Area теги

| Area | Scope |
|------|-------|
| `client` | Коммуникация с клиентом, онбординг, бриф |
| `design` | Мудборд, визуальные решения, референсы |
| `dev` | Верстка HTML/CSS/JS, разработка сайта |
| `deploy` | Деплой на Netlify, проверка сайта |
| `comms` | Тон общения, формулировки, подача |
| `config` | Конфиги, шаблоны, структура папок |

## Периодический review

Просматривать `.learnings/` перед новым проектом или раз в неделю:

```bash
# Сколько незакрытых записей
grep -h "Status\*\*: pending" .learnings/*.md | wc -l

# Высокоприоритетные незакрытые
grep -B5 "Priority\*\*: high" .learnings/*.md | grep "^## \["
```
