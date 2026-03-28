---
name: Site Deploy
description: Деплой сайта на Netlify CLI. Проверка после деплоя.
read_when:
  - Нужно задеплоить сайт клиента
  - Code review пройден, оператор апрувнул деплой
allowed-tools: Bash(netlify:*), Bash(npx netlify-cli:*)
---

# Site Deploy — Netlify

## Требования

```bash
npm install -g netlify-cli
netlify login  # один раз, интерактивно
```

## Деплой

```bash
cd clients/{chat_id}/artifacts/site

# Тестовый деплой (preview URL, не production)
netlify deploy --dir=.

# Production деплой (только после апрува оператора)
netlify deploy --dir=. --prod
```

## Первый деплой нового сайта

```bash
# Создать новый сайт на Netlify
netlify deploy --dir=. --prod

# Или с именем
netlify deploy --dir=. --prod --site-name=client-{chat_id}
```

## Верификация после деплоя

После получения URL — обязательно проверь:

```bash
# Скриншот задеплоенного сайта
agent-browser open {deploy_url}
agent-browser wait --load networkidle
agent-browser screenshot --full clients/{chat_id}/artifacts/deployed_preview.png

# Мобилка
agent-browser set device "iPhone 14"
agent-browser open {deploy_url}
agent-browser screenshot --full clients/{chat_id}/artifacts/deployed_preview_mobile.png
```

Проверь:

- [ ] Сайт открывается (не 404, не ошибка)
- [ ] Стили загрузились
- [ ] Изображения отображаются
- [ ] Мобилка выглядит корректно

## Формат результата

```
DEPLOY: ✅
URL: https://...
Preview: clients/{chat_id}/artifacts/deployed_preview.png
```

Или при ошибке:

```
DEPLOY: ❌
Error: {сообщение}
Action: {что нужно сделать}
```

## Кастомный домен (если есть)

```bash
# Добавить домен в Netlify (через dashboard или CLI)
netlify sites:list  # найти site ID
# Настройка DNS делается в панели домена клиента
```

## Troubleshooting

- `netlify login` не работает без браузера → используй `netlify login --no-open` и следуй инструкциям
- 404 на ресурсах → проверь относительные пути в HTML
- Стили не загружаются → проверь путь к `style.css` в `<link>`
