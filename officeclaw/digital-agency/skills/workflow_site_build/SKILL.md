---
name: Workflow — Разработка и деплой сайта
description: Полный цикл на основе Astro + shadcn шаблона: копирование шаблона → кастомизация темы → сборка страниц → деплой.
read_when:
  - Мудборд апрувнут клиентом и можно переходить к разработке сайта
  - brief.md содержит moodboard.status = approved
---

# Workflow: Разработка и деплой сайта

## Стек

- **Astro 5** — фреймворк (страницы, layouts, статические компоненты)
- **React 19** — интерактивные острова (`client:load`)
- **Tailwind CSS 4** + **shadcn v4** (`radix-maia` стиль) — UI компоненты
- **HugeIcons** — иконки (`@hugeicons/react`)

## Вход

**HARD GATE — не продолжай без этой проверки:**

Открой `clients/{chat_id}/brief.md` и убедись что:

1. Поле `moodboard.status` существует и равно `approved`
2. Поле `moodboard.pinterest_url` заполнено

Если мудборд не апрувнут → **STOP**.
Сообщи оператору: "Сайт нельзя начинать без согласованного мудборда. Текущий статус мудборда: {status}"
Переходи в фазу MOODBOARD.

---

## Фазы

### Фаза 1 — Планирование

Прочитай `clients/{chat_id}/brief.md`. Зафиксируй в `clients/{chat_id}/artifacts/site_plan.md`:

```yaml
pages:
  - name: index
    sections:
      - type: hero # Hero с заголовком и CTA
      - type: services # Карточки услуг
      - type: about # О компании
      - type: testimonials # Отзывы
      - type: faq # Аккордеон с вопросами
      - type: cta # Финальный призыв
      - type: footer # Подвал

theme:
  primary_color: "#..." # Основной цвет из мудборда
  font: "..." # Шрифт
  tone: light | dark # Светлая или тёмная тема

components_needed:
  - button # Уже в шаблоне
  - card
  - accordion
  - badge
  - separator
  - ... # Только то, что реально нужно
```

---

### Фаза 2 — Копирование шаблона

Разработку выполняет Claude Code агент. Подготовь задание и запусти его через bash:

```bash
claude --print "{промпт}" --output-format text
```

**Промпт для агента:**

````
Ты разрабатываешь лендинг для клиента на основе готового Astro + shadcn шаблона.

## DESIGN MANDATE — ОБЯЗАТЕЛЬНО

**Прочитай скилл `frontend_design` перед любой работой с темой и компонентами.**

Правила которые нельзя нарушать:
- Выбери конкретное эстетическое направление и выполни его с полной отдачей (брутальный минимализм, максимализм, editorial, luxury, retro-futuristic — что угодно, но ОДНО и до конца)
- НЕ используй Inter, Roboto, Arial, Space Grotesk, system fonts — выбери характерный шрифт
- НЕ делай фиолетовые градиенты на белом — это generic AI slop
- Каждый сайт должен быть незабываемым. Что запомнит клиент через неделю?
- Смелость важнее безопасности. Лучше необычный и спорный, чем правильный и скучный.

## Бриф
{полное содержимое brief.md}

## Site plan
{содержимое site_plan.md}

## Шаги

### 1. Скопировать шаблон
Скопируй шаблон в директорию клиента (без node_modules и .git):

```bash
rsync -av --exclude='node_modules' --exclude='.git' --exclude='.astro' \
  {AGENT_DIR}/skills/workflow_site_build/assets/website/ \
  clients/{chat_id}/artifacts/site/
````

### 2. Установить зависимости

```bash
cd clients/{chat_id}/artifacts/site
pnpm install
```

### 3. Настроить тему

Отредактируй `src/styles/global.css` — замени CSS переменные в блоке `:root` на цвета из мудборда клиента.

Цвета задаются в формате oklch(). Конвертируй HEX → oklch через формулу или используй
oklch-значения из схемы shadcn (https://ui.shadcn.com/themes).

Будь очень смелым при написании темы - основная цель сделать максимально уникальный и крутой дизайн. Обязательно используй скилл /frontend-design

````

Шрифт: замени `@fontsource-variable/figtree` в global.css на нужный, добавь пакет в package.json.
Если шрифт не нужно менять — оставь Figtree.

### 4. Обновить layout

В `src/layouts/main.astro` обнови `<title>` и добавь нужные meta теги (description, og:title и т.д.)

### 5. Создать компоненты секций

Для каждой секции из site_plan.md создай файл в `src/components/sections/`:

- `HeroSection.tsx` (или `.astro` если нет интерактивности)
- `ServicesSection.tsx`
- `AboutSection.tsx`
- и т.д.

**Правила компонентов:**

- Используй shadcn компоненты из `@/components/ui/` (они уже установлены)
- Используй HugeIcons: `import { IconName } from "@hugeicons/core-free-icons"; import { HugeiconsIcon } from "@hugeicons/react";`
- Для React-компонентов: `.tsx` файл + `client:load` при вставке в `.astro`
- Для статических секций без JS: `.astro` файл
- Mobile-first через Tailwind breakpoints (`md:`, `lg:`)
- Тексты берёшь из brief.md (название, описание, услуги и т.д.)

Пример Hero секции:

```tsx
// src/components/sections/HeroSection.tsx
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function HeroSection() {
  return (
    <section className="min-h-screen flex items-center justify-center px-6 py-24">
      <div className="max-w-4xl mx-auto text-center">
        <Badge variant="outline" className="mb-6">
          Ваш тег
        </Badge>
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
          Заголовок из брифа
        </h1>
        <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
          Подзаголовок из брифа
        </p>
        <div className="flex gap-4 justify-center flex-wrap">
          <Button size="lg">Основной CTA</Button>
          <Button size="lg" variant="outline">
            Вторичный CTA
          </Button>
        </div>
      </div>
    </section>
  );
}
````

### 6. Собрать index.astro

В `src/pages/index.astro` импортируй и расставь все секции:

```astro
---
import Layout from "@/layouts/main.astro"
import { HeroSection } from "@/components/sections/HeroSection"
import { ServicesSection } from "@/components/sections/ServicesSection"
// ...
---

<Layout>
  <HeroSection client:load />
  <ServicesSection client:load />
  <!-- ... -->
</Layout>
```

Если секция статическая (без состояния/анимаций) — используй `.astro` компонент без `client:load`.

### 7. Проверить сборку

```bash
cd clients/{chat_id}/artifacts/site
pnpm build
```

Если сборка упала — исправь ошибки и повтори.

### 8. Сделать скриншот

После успешной сборки запусти preview:

```bash
pnpm preview &
```

Дай серверу 3 секунды запуститься. Затем сделай скриншот через agent_browser.

````

Дождись завершения агента. Если агент вернул ошибку сборки — уведоми оператора.

---

### Фаза 3 — Локальная проверка

**Прочитай скилл `code_review` и выполни review перед деплоем.**

После завершения агента проверь:
```bash
cd clients/{chat_id}/artifacts/site
pnpm preview
```

Используй `agent_browser` для проверки:

- Десктоп (1440px)
- Мобилка (375px)
- Нет консольных ошибок

Чеклист:

- [ ] Тема соответствует мудборду
- [ ] Все секции отображаются корректно
- [ ] Адаптив работает на 375px
- [ ] Все ссылки/кнопки реагируют на клик
- [ ] Нет TypeScript/build ошибок

---

## Выход

Зафикси в `clients/{chat_id}/artifacts/phase_site_summary.yaml`:

```yaml
status: delivered
url: https://...
deployed_at: { timestamp }
stack: astro5-shadcn-radix-maia
client_notified: true
```

---

## Шпаргалка: shadcn компоненты в шаблоне

Все компоненты уже установлены в `src/components/ui/`. Используй как:

```tsx
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  NavigationMenu,
  NavigationMenuList,
  NavigationMenuItem,
  NavigationMenuLink,
} from "@/components/ui/navigation-menu";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
```

## Шпаргалка: HugeIcons

```tsx
import { Home01Icon, ArrowRight01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";

<HugeiconsIcon icon={Home01Icon} size={24} color="currentColor" />;
```
