# Agent Vertical Design Model

*Март 2026 | Ментальная модель для проектирования агентных вертикалей*

---

## TL;DR

Tractability агента определяется не сложностью задачи, а **verbalizability домена** — насколько хорошо знания и решения в этом домене можно выразить в тексте и структуре. Repo — это граница вербализованного контекста. Checkpoints — не UX, а архитектурные границы где verbalizability кончается.

---

## 1. Verbalizability как главный критерий

Когда мы оцениваем агентную вертикаль, неправильный вопрос: "насколько сложная задача?". Правильный: "насколько этот домен можно вербализовать?"

**Вербализуемо** — можно точно записать в текст или структуру:
- Код, типы, тесты
- Бриф с требованиями
- Структура сайта (YAML)
- Финансовые правила и compliance
- Технические спецификации

**Невербализуемо** — требует человеческой оценки:
- "Нравится ли клиенту"
- "Выглядит ли это круто"
- Эстетические предпочтения без явного брифа
- Стратегические бизнес-интуиции

### Матрица tractability

|  | Низкая verbalizability | Высокая verbalizability |
|--|--|--|
| **Чёткие quality signals** | Трудно действовать, легко оценить (e-commerce CTR, рекомендации) | **Золотая зона**: высокая автономия (SaaS dev, legal, finance) |
| **Размытые quality signals** | Тяжелее всего (pure aesthetics, community mgmt) | **Хорошая зона с checkpoints**: автономия внутри фазы (design agency, edtech, research) |

**Design agency** живёт в правом нижнем квадранте — хорошая зона. Агент автономен в исполнении (бриф, код, деплой), но нужны checkpoints там где verbalizability кончается (эстетика мудборда, готовность к показу клиенту).

---

## 2. Repo как граница вербализованного контекста

Repo — это не просто хранилище файлов. Это **граница между тем что агент контролирует автономно и тем что требует человека**.

```
┌─────────────────────────────────────────────┐
│  Внешний мир                                 │
│  (тренды, клиентские вкусы, рынок)           │
│  ┌───────────────────────────────────────┐   │
│  │  Checkpoints                           │   │
│  │  (невербализуемые решения → человек)   │   │
│  │  ┌─────────────────────────────────┐  │   │
│  │  │  Repo = агентная автономия       │  │   │
│  │  │  (brief, artifacts, state,       │  │   │
│  │  │   knowledge base, skills)        │  │   │
│  │  └─────────────────────────────────┘  │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**Ключевые выводы:**
- Что попадает в repo — определяется verbalizability
- Checkpoint ставится ровно там где verbalizability кончается
- Итерация = попытка вербализовать больше → расширение repo
- Knowledge flywheel: агент учится описывать то что раньше только человек мог оценить

**Дизайн-вопрос для любой вертикали:** что ты кладёшь в repo? Это и есть твоя вертикаль.

---

## 3. Operation Archetypes

Правильная единица классификации — не продукт ("SaaS агент", "agency агент"), а **тип операции**. Реальный бизнес комбинирует несколько archetypes. Это первая попытка разбиения — рафинируется через практику.

### Episodic (agency model)
- **Операция:** проект начался → доставлен → архив. Конечная точка есть.
- **Repo форма:** `clients/{id}/artifacts/` — организован вокруг проектов
- **Checkpoint:** phase gates (approval между фазами)
- **Knowledge flywheel:** паттерны по клиентам, ICP — медленный
- **Trigger:** reactive (клиент пишет) + cron (research фон)
- **Примеры:** design agency, юридические услуги, consulting, recruiting

### Continuous (ops model)
- **Операция:** нет конечной точки, состояние накапливается, отношения углубляются
- **Repo форма:** `contacts/{id}/history/` — организован вокруг отношений
- **Checkpoint:** escalation triggers (аномалия, порог, нестандартный случай)
- **Knowledge flywheel:** глубина отношений — быстрый
- **Trigger:** events (CRM update, inbound lead, support ticket)
- **Примеры:** CRM / B2B sales ops, customer support, account management

### Intelligence (research model)
- **Операция:** сбор → синтез → поверхностирование инсайтов
- **Repo форма:** `intelligence/{topic}/` — организован вокруг знаний
- **Checkpoint:** почти нет (notification only)
- **Knowledge flywheel:** сигналы рынка, паттерны — быстрый
- **Trigger:** cron-heavy (мониторинг, регулярный сбор)
- **Примеры:** competitor intel, lead research, trend monitoring, market analysis

### Content (media model)
- **Операция:** ритмичный цикл создания и дистрибуции
- **Repo форма:** `content/{date}/` + audience model
- **Checkpoint:** editorial review перед публикацией (irreversible action)
- **Knowledge flywheel:** что заходит аудитории — быстрый
- **Trigger:** cron (расписание) + reactive (тренды, события)
- **Примеры:** social media, newsletter, edtech curriculum, SEO

### Где Claude Code, не async агент
Code writing = синхронный, tight feedback loop к коду, оператор рядом. Async агент — асинхронный, работает когда оператора нет, накапливает знания, уведомляет когда нужно решение. Это разные режимы, не конкуренты.

---

## 4. Proto-Market Entity Skeleton

Шаблон для проектирования любой агентной вертикали. Заполни 6 компонентов — сразу видно что в repo, где checkpoints, какой archetype доминирует.

### Компонент 1: Market Scope
- Какой рынок обслуживает
- Кто principal (оператор), кто внешний клиент
- Какую ценность создаёт

### Компонент 2: Repo Structure
Форма зависит от доминирующего operation archetype. Вопрос: что можно точно записать в текст/структуру?

- Что живёт в repo (вербализованный контекст)
- Что НЕ попадает в repo (→ checkpoint)
- Shared knowledge (global/ — паттерны, world model)

### Компонент 3: Operation Mix
Какие archetypes активны и в каких пропорциях. Один доминирует, остальные фоновые.

```
Episodic    ●●●●○
Intelligence ●●○○○
Content     ●○○○○
Continuous  ○○○○○
```

### Компонент 4: Trigger Portfolio
- **Reactive:** что приходит от внешнего клиента / оператора
- **Cron:** что агент делает сам по расписанию
- **Event:** что запускается автоматически по состоянию (phase complete, threshold crossed)

### Компонент 5: Checkpoint Map
Архитектурные границы где verbalizability кончается. Каждый checkpoint = граница repo.

Для каждого checkpoint:
- Что именно невербализуемо
- Кто принимает решение (оператор / клиент)
- Blocking (агент ждёт) или passive (агент продолжает, фиксирует)

### Компонент 6: Knowledge Flywheel
Что накапливается в repo со временем. Это compound value — что отличает агента от инструмента.

- Day 1: что агент знает из коробки
- Month 1: что начинает накапливаться
- Month 6: как меняется поведение агента

---

## 5. Пример: Design Agency

### Market Scope
Дизайн-студия для малого бизнеса. Principal = оператор (founder). Внешний клиент = бизнес заказывающий сайт. Ценность: от идеи до задеплоенного сайта без найма команды.

### Repo Structure
```
clients/{chat_id}/
  brief.md              ← вербализованные требования
  artifacts/
    moodboard.md        ← ссылки + mood words
    site_plan.md        ← структура сайта (YAML)
    site/               ← собранный сайт
    phase_*.yaml        ← structured summaries
global/
  patterns/             ← накопленные ICP паттерны
  world_model.md        ← знания о рынке
```
НЕ в repo: "нравится ли клиенту эстетика" → checkpoint.

### Operation Mix
```
Episodic    ●●●●○  — основной флоу requirements → moodboard → site → deploy
Intelligence ●●○○○  — фоновый мониторинг трендов, конкурентов
Content     ●○○○○  — опционально: кейсы, портфолио
```

### Trigger Portfolio
- **Reactive:** inbound сообщение клиента → onboarding / requirements / текущая фаза
- **Cron (weekly):** scan трендов дизайна → обновить global/trends/
- **Event:** `moodboard.status = approved` → автоматически запустить site_build

### Checkpoint Map
| Checkpoint | Почему невербализуемо | Тип |
|--|--|--|
| Moodboard approval | Эстетические предпочтения клиента | Blocking (клиент) |
| Pre-deploy review | Готовность к публичной демонстрации | Blocking (оператор) |
| Scope/pricing change | Бизнес-решение | Blocking (оператор) |

### Knowledge Flywheel
- **Day 1:** агент спрашивает всё, нет контекста о клиенте
- **Month 1:** паттерны вкусов первых клиентов, ICP профиль в `global/`
- **Month 6:** агент предугадывает бриф по типу клиента, verbalizability расширилась

---

## 6. Как итерировать

**Принцип:** каждая итерация отвечает на вопрос — можем ли мы вербализовать больше?

1. **Запусти вертикаль** с минимальным repo. Зафиксируй где агент застревает.
2. **Найди паттерн** в checkpoint'ах — что оператор решает снова и снова?
3. **Вербализуй** — если паттерн повторяется, его можно описать в SKILL.md или brief структуре.
4. **Перенеси в repo** — checkpoint исчезает или становится редким.
5. **Повтори** — flywheel работает.

**Признак хорошей итерации:** оператор реже вмешивается в одно и то же решение.

**Признак плохой итерации:** добавляешь сложность без конкретного невербализованного паттерна который хочешь закрыть.

---

## Связь с nanobot runtime

Эта ментальная модель работает поверх текущего nanobot:

- **Repo Structure** → workspace layout (`clients/`, `global/`, `skills/`)
- **Trigger Portfolio** → reactive (channel messages) + cron (nanobot cron service)
- **Checkpoint Map** → AGENTS.md BLOCKING ACTIONS + confidence rules
- **Knowledge Flywheel** → memory consolidation (MEMORY.md, HISTORY.md)
- **Operation Mix** → определяет приоритет skills в AGENTS.md

Для прототипа (Phase 0–1) checkpoints реализуются prompt-level. Для Phase 2+ — runtime blocking actions guard (см. `runtime_diff_proposals.md`).
