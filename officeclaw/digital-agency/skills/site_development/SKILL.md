---
name: Site Development
description: Стандарты и возможности для создания HTML/CSS/JS лендингов. Качественные критерии, паттерны, типографика.
read_when:
  - Пишешь HTML/CSS/JS для сайта клиента
  - Нужно знать стандарты качества для верстки
  - Реализуешь дизайн из брифа или мудборда
---

# Site Development

## Возможности

Создаю лендинги и микросайты:
- Ванильный HTML5/CSS3/JS (без фреймворков для простых сайтов)
- Адаптивная верстка (mobile-first)
- CSS animations и transitions
- Scroll-based эффекты
- Контактные формы (Netlify Forms, Formspree)
- Подключение Google Fonts, иконок

## Качественные критерии

### Performance
- Lighthouse Performance ≥ 85
- Lighthouse SEO ≥ 90
- Изображения: WebP формат предпочтителен, max 300KB без reason
- JS: `defer` или `async` для внешних скриптов
- CSS: критические стили инлайн в `<head>` если >100ms до FCP

### Mobile
- Viewport: `<meta name="viewport" content="width=device-width, initial-scale=1">`
- Breakpoint: 375px (iPhone SE) — минимальная поддерживаемая ширина
- Touch targets: кнопки/ссылки ≥ 44×44px
- Нет горизонтального скролла

### SEO и Social
- `<title>` уникальный, 50–60 символов
- `<meta name="description">` 120–160 символов
- OG теги: `og:title`, `og:description`, `og:image`, `og:url`
- `og:image`: 1200×630px
- Семантичный HTML: `<header>`, `<main>`, `<section>`, `<footer>`, `<nav>`

### Accessibility
- Alt text для всех `<img>`
- Иерархия заголовков: один `<h1>`, затем `<h2>` и т.д.
- Контраст текст/фон: WCAG AA (4.5:1 для обычного текста)
- `lang` атрибут на `<html>`

## Структура файлов

```
site/
├── index.html        # единственный HTML файл для лендинга
├── style.css         # все стили
├── script.js         # JS если нужен
└── assets/
    ├── images/       # оптимизированные изображения
    └── fonts/        # локальные шрифты если нужны
```

## CSS паттерны

```css
/* Переменные — всегда */
:root {
  --color-primary: #...;
  --color-bg: #...;
  --font-heading: 'Font Name', serif;
  --font-body: 'Font Name', sans-serif;
}

/* Mobile-first breakpoints */
/* base — mobile */
@media (min-width: 768px) { /* tablet */ }
@media (min-width: 1200px) { /* desktop */ }

/* Container */
.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}
```

## HTML шаблон

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>...</title>
  <meta name="description" content="...">
  <!-- OG -->
  <meta property="og:title" content="...">
  <meta property="og:description" content="...">
  <meta property="og:image" content="...">
  <meta property="og:url" content="...">
  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=...&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>...</header>
  <main>
    <section id="hero">...</section>
    <section id="about">...</section>
    <!-- ... -->
  </main>
  <footer>...</footer>
  <script src="script.js" defer></script>
</body>
</html>
```

## Когда нужен JS

JS нужен только для:
- Hamburger menu на мобилке
- Smooth scroll
- Form submission (если без Netlify Forms)
- Простые анимации которые нельзя сделать на CSS

Всё что можно сделать на CSS — делай на CSS.
