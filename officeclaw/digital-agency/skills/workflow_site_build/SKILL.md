---
name: Workflow — Разработка и деплой сайта
description: Полный цикл: чтение брифа → разработка → code review → деплой → верификация.
read_when:
  - Мудборд апрувнут или клиент готов к разработке сайта
  - Бриф содержит достаточно информации для старта
  - Клиент попросил сделать лендинг
---

# Workflow: Разработка и деплой сайта

## Вход

Перед стартом убедись что есть:
- `clients/{chat_id}/brief.md` с заполненными полями
- Понимание визуального направления (из мудборда или из брифа)

## Фазы

### Фаза 1 — Планирование структуры

До написания кода определи:
- Секции лендинга (Hero, About, Services, CTA, Footer и т.д.)
- Ключевые сообщения для каждой секции
- Цветовая палитра и типографика

Зафикси решения в `clients/{chat_id}/artifacts/site_plan.md`.

CONFIDENCE check: если не уверен в структуре → прочитай бриф ещё раз, при необходимости уточни у оператора.

### Фаза 2 — Разработка

Читай скилл `site_development` — там стандарты кода и качественные критерии.

Создавай файлы в `clients/{chat_id}/artifacts/site/`:
```
site/
├── index.html
├── style.css
└── script.js    # только если нужен JS
```

Принципы:
- Ванильный HTML/CSS/JS — никаких фреймворков для простых лендингов
- Mobile-first
- Семантичный HTML

### Фаза 3 — Code Review

Читай скилл `code_review` и прогони все файлы через него.
Исправь все CRITICAL и HIGH issues.

### Фаза 4 — Локальная проверка

```bash
# Запусти локальный сервер
cd clients/{chat_id}/artifacts/site
python3 -m http.server 8080
```

Используй `browser_use` для проверки:
```bash
agent-browser open http://localhost:8080
agent-browser screenshot --full preview.png
agent-browser set device "iPhone 14"
agent-browser screenshot --full preview_mobile.png
```

Проверь:
- [ ] Десктоп выглядит корректно
- [ ] Мобилка 375px выглядит корректно
- [ ] Все ссылки работают
- [ ] Нет консольных ошибок

### Фаза 5 — Апрув оператора

Это **blocking action**. Сформируй карточку:

```
🔴 ТРЕБУЕТ АПРУВ: Деплой сайта

Клиент: {chat_id}
Lighthouse preview: {если есть}
Мобилка: ✅/⚠️
Ссылки: ✅

Скриншоты приложены.

[✅ Деплоить] [🔧 Доработать] [❌ Отменить]
```

### Фаза 6 — Деплой

Читай скилл `site_deploy` и деплой на Netlify.

### Фаза 7 — Отправка клиенту

Это **blocking action** (`send_to_client`).

Когда получен деплой URL → сформируй карточку для оператора с ссылкой и скриншотом.
После апрува → отправь клиенту.

## Выход

Зафикси в `clients/{chat_id}/artifacts/phase_site_summary.yaml`:
```yaml
status: delivered
url: https://...
deployed_at: {timestamp}
lighthouse_score: {score}
client_notified: true
```
