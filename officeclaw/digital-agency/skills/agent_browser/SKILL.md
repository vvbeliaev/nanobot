---
name: Agent Browser
description: A fast headless browser CLI (agent-browser) for navigating pages, clicking, filling forms, and taking screenshots.
read_when:
  - Нужно открыть сайт или веб-приложение
  - Собираешь визуальные референсы (Pinterest, Behance, Dribbble)
  - Проверяешь задеплоенный сайт клиента
  - Нужно взаимодействовать с UI — кликать, заполнять формы
metadata: {"clawdbot":{"emoji":"🌐","requires":{"bins":["node","npm"]}}}
allowed-tools: Bash(agent-browser:*)
---

# Browser Automation with agent-browser

## Installation

```bash
npm install -g agent-browser
agent-browser install
```

## Quick start

**Всегда используй CDP режим** — реальный Brave браузер, не детектируется антиботами:

```bash
agent-browser --cdp 19900 open <url>        # Navigate to page
agent-browser --cdp 19900 snapshot -i       # Get interactive elements with refs
agent-browser --cdp 19900 click @e1         # Click element by ref
agent-browser --cdp 19900 fill @e2 "text"   # Fill input by ref
```

Если браузер не запущен — запусти скрипт:
```bash
./scripts/start-browser.sh
```

## Core workflow

1. Navigate: `agent-browser open <url>`
2. Snapshot: `agent-browser snapshot -i` (returns elements with refs like `@e1`, `@e2`)
3. Interact using refs from the snapshot
4. Re-snapshot after navigation or significant DOM changes

## Commands

### Navigation

```bash
agent-browser open <url>      # Navigate to URL
agent-browser back            # Go back
agent-browser forward         # Go forward
agent-browser reload          # Reload page
agent-browser close           # Close browser
```

### Snapshot (page analysis)

```bash
agent-browser snapshot            # Full accessibility tree
agent-browser snapshot -i         # Interactive elements only (recommended)
agent-browser snapshot -c         # Compact output
agent-browser snapshot -d 3       # Limit depth to 3
agent-browser snapshot -s "#main" # Scope to CSS selector
```

### Interactions (use @refs from snapshot)

```bash
agent-browser click @e1           # Click
agent-browser dblclick @e1        # Double-click
agent-browser fill @e2 "text"     # Clear and type
agent-browser type @e2 "text"     # Type without clearing
agent-browser press Enter         # Press key
agent-browser scroll down 500     # Scroll page
agent-browser drag @e1 @e2        # Drag and drop
```

### Get information

```bash
agent-browser get text @e1        # Get element text
agent-browser get html @e1        # Get innerHTML
agent-browser get value @e1       # Get input value
agent-browser get attr @e1 href   # Get attribute
agent-browser get title           # Get page title
agent-browser get url             # Get current URL
```

### Screenshots & PDF

```bash
agent-browser screenshot          # Screenshot to stdout
agent-browser screenshot path.png # Save to file
agent-browser screenshot --full   # Full page
agent-browser pdf output.pdf      # Save as PDF
```

### Wait

```bash
agent-browser wait @e1                     # Wait for element
agent-browser wait 2000                    # Wait milliseconds
agent-browser wait --text "Success"        # Wait for text
agent-browser wait --url "/dashboard"      # Wait for URL pattern
agent-browser wait --load networkidle      # Wait for network idle
```

### Browser settings

```bash
agent-browser set viewport 1920 1080      # Set viewport size
agent-browser set device "iPhone 14"      # Emulate mobile device
agent-browser set media dark              # Emulate dark color scheme
```

### Tabs

```bash
agent-browser tab new [url]       # New tab
agent-browser tab 2               # Switch to tab
agent-browser tab close           # Close tab
```

### JavaScript

```bash
agent-browser eval "document.title"   # Run JavaScript
```

## Sessions (parallel browsers)

```bash
agent-browser --session test1 open site-a.com
agent-browser --session test2 open site-b.com
agent-browser session list
```

## JSON output (for parsing)

```bash
agent-browser snapshot -i --json
agent-browser get text @e1 --json
```

## Debugging

```bash
agent-browser open example.com --headed   # Show browser window
agent-browser console                     # View console messages
agent-browser errors                      # View page errors
```

## Troubleshooting

- If element is not found, use snapshot to find the correct ref
- Always re-snapshot after navigation to get fresh refs
- Use `--headed` to see the browser window for debugging
- Use `fill` instead of `type` for input fields to ensure existing text is cleared
