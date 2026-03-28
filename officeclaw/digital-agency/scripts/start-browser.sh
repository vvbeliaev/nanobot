#!/bin/bash
# Запускает Brave с профилем digital-agency на порту 19900

PROFILE_DIR="$(cd "$(dirname "$0")/.." && pwd)/browser-profile"
PORT=19900

# Проверяем не запущен ли уже
if curl -s "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "Browser already running on port $PORT"
  exit 0
fi

# Чистим stale lock-файлы от предыдущих упавших сессий
rm -f "$PROFILE_DIR/SingletonLock" "$PROFILE_DIR/SingletonSocket" "$PROFILE_DIR/SingletonCookie"

nohup /Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser \
  --remote-debugging-port=$PORT \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --disable-sync \
  >/dev/null 2>&1 &

# Ждём запуска
for i in {1..10}; do
  sleep 1
  if curl -s "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    echo "Browser ready on port $PORT"
    exit 0
  fi
done

echo "Browser failed to start"
exit 1
