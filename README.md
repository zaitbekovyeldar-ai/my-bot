# my-bot

Telegram-бот, который отвечает через Claude и помнит контекст диалога.

Команды: `/start` — приветствие, `/reset` — очистить контекст.

## Что понадобится

- Токен Telegram-бота: в [@BotFather](https://t.me/BotFather) команда `/newbot` (или `/token` для существующего бота).
- Ключ Anthropic API: https://console.anthropic.com/settings/keys

**Никогда не коммить ключи и не присылай их в чаты.** Они хранятся только в файле `.env`, который git игнорирует.

## Запуск на своём компьютере

```bash
git clone https://github.com/zaitbekovyeldar-ai/my-bot.git
cd my-bot
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # затем впиши ключи в .env
python bot.py
```

Открой своего бота в Telegram и напиши ему что-нибудь.

## Запуск на сервере (Ubuntu/Debian, systemd)

Бот работает постоянно и сам перезапускается после сбоя или перезагрузки сервера.

```bash
# 1. Зайти на сервер
ssh root@<IP-сервера>

# 2. Поставить Python и создать отдельного пользователя для бота
apt update && apt install -y python3 python3-venv git
adduser --disabled-password --gecos "" botuser

# 3. Скачать код и установить зависимости
su - botuser
git clone https://github.com/zaitbekovyeldar-ai/my-bot.git
cd my-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env                        # вписать ключи, сохранить: Ctrl+O, Enter, Ctrl+X
chmod 600 .env
exit                             # вернуться в root

# 4. Включить сервис
cp /home/botuser/my-bot/my-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now my-bot
```

Полезные команды:

```bash
systemctl status my-bot          # работает ли бот
journalctl -u my-bot -f          # логи в реальном времени
systemctl restart my-bot         # перезапуск (например, после git pull)
```

Обновить бота: `su - botuser -c "cd my-bot && git pull"`, затем `systemctl restart my-bot`.

## Настройки (`.env`)

| Переменная | По умолчанию | Что делает |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | токен от BotFather (обязательно) |
| `ANTHROPIC_API_KEY` | — | ключ Anthropic API (обязательно) |
| `CLAUDE_MODEL` | `claude-opus-5-5` | модель Claude |
| `CLAUDE_EFFORT` | `low` | глубина рассуждений: `low`, `medium`, `high` |
| `MAX_HISTORY` | `20` | сколько последних сообщений помнить |
| `SYSTEM_PROMPT` | дружелюбный помощник | характер и правила бота |

История диалогов хранится в памяти и обнуляется при перезапуске бота.
