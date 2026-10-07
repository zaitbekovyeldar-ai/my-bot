#!/usr/bin/env bash
# Установка бота на сервер Ubuntu одной командой (запускать от root):
#   bash <(curl -fsSL https://raw.githubusercontent.com/zaitbekovyeldar-ai/my-bot/claude/zen-galileo-1rxidi/install.sh)
# Ключи скрипт спрашивает сам: они не выводятся на экран и не попадают в историю.

clear
echo "=== Установка бота ==="
read -rsp "1) Вставь токен Telegram-бота и нажми Enter (символы не видны): " TG < /dev/tty; echo
read -rsp "2) Вставь ключ Anthropic и нажми Enter: " AK < /dev/tty; echo
TG="${TG//[[:space:]]/}"; AK="${AK//[[:space:]]/}"
echo "⏳ Проверяю ключи..."
code=$(curl -s -o /dev/null -w '%{http_code}' "https://api.telegram.org/bot${TG}/getMe")
[ "$code" = 200 ] || { echo "❌ Telegram не принял токен (код $code). Возьми актуальный токен в @BotFather и запусти заново."; exit 1; }
code=$(curl -s -o /dev/null -w '%{http_code}' https://api.anthropic.com/v1/models -H "x-api-key: ${AK}" -H "anthropic-version: 2023-06-01")
[ "$code" = 200 ] || { echo "❌ Anthropic не принял ключ (код $code). Нужен API-ключ с https://platform.claude.com → API Keys → Create Key. Запусти заново."; exit 1; }
echo "✅ Оба ключа рабочие"

echo "⏳ Ставлю пакеты..."
DEBIAN_FRONTEND=noninteractive apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv git >/dev/null || { echo "❌ Не удалось поставить пакеты"; exit 1; }
id botuser >/dev/null 2>&1 || adduser --disabled-password --gecos "" botuser >/dev/null

echo "⏳ Скачиваю код..."
D=/home/botuser/my-bot
if [ -d "$D/.git" ]; then
  sudo -u botuser git -C "$D" pull -q
else
  sudo -u botuser env GIT_TERMINAL_PROMPT=0 git clone -q -b claude/zen-galileo-1rxidi https://github.com/zaitbekovyeldar-ai/my-bot.git "$D" \
    || { echo "❌ Не удалось скачать код. Репозиторий должен быть публичным (GitHub → Settings → Change visibility → Public)."; exit 1; }
fi

echo "⏳ Ставлю библиотеки Python..."
sudo -u botuser python3 -m venv "$D/.venv" && sudo -u botuser "$D/.venv/bin/pip" install -q -r "$D/requirements.txt" || { echo "❌ Не удалось поставить библиотеки"; exit 1; }

printf 'TELEGRAM_BOT_TOKEN=%s\nANTHROPIC_API_KEY=%s\n' "$TG" "$AK" > "$D/.env"
chown botuser:botuser "$D/.env"; chmod 600 "$D/.env"
unset TG AK

echo "⏳ Запускаю бота..."
cp "$D/my-bot.service" /etc/systemd/system/my-bot.service
systemctl daemon-reload
systemctl enable -q my-bot
systemctl restart my-bot
sleep 5
if systemctl is-active -q my-bot; then
  echo "✅ Бот запущен! Напиши ему в Telegram."
else
  echo "❌ Бот не запустился. Последние строки лога:"
fi
journalctl -u my-bot -n 15 --no-pager
