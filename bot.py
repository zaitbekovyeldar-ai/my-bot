"""Telegram-бот, который отвечает через Claude и помнит контекст диалога."""

import logging
import os
from collections import defaultdict

import anthropic
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
# Для чата хватает низкого усилия: ответы быстрее и дешевле.
EFFORT = os.getenv("CLAUDE_EFFORT", "low")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Ты дружелюбный помощник в Telegram. Отвечай кратко и по делу, "
    "на языке собеседника.",
)
TELEGRAM_LIMIT = 4096

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("bot")

# ANTHROPIC_API_KEY берётся из окружения автоматически.
claude = anthropic.AsyncAnthropic()

# История диалогов в памяти: chat_id -> список сообщений.
# После перезапуска бота история обнуляется.
histories: dict[int, list[dict]] = defaultdict(list)


def trim_history(history: list[dict]) -> None:
    """Оставляет последние MAX_HISTORY сообщений; первое всегда от user."""
    del history[: max(0, len(history) - MAX_HISTORY)]
    while history and history[0]["role"] != "user":
        history.pop(0)


async def ask_claude(history: list[dict]) -> str:
    response = await claude.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=history,
        output_config={"effort": EFFORT},
        # Если модель откажется отвечать, API сам попробует запасную модель.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        return "Извини, на это я ответить не могу."
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text or "…"


def split_message(text: str) -> list[str]:
    """Режет длинный ответ на части, которые влезают в одно сообщение Telegram."""
    parts = []
    while len(text) > TELEGRAM_LIMIT:
        cut = text.rfind("\n", 0, TELEGRAM_LIMIT)
        if cut <= 0:
            cut = TELEGRAM_LIMIT
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    parts.append(text)
    return parts


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот на Claude. Пиши что угодно — я отвечу.\n"
        "/reset — начать диалог заново."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    histories.pop(update.effective_chat.id, None)
    await update.message.reply_text("Контекст очищен. Начнём сначала!")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    history = histories[chat_id]
    history.append({"role": "user", "content": update.message.text})
    trim_history(history)

    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    try:
        answer = await ask_claude(history)
    except anthropic.RateLimitError:
        history.pop()
        await update.message.reply_text("Слишком много запросов, попробуй через минуту.")
        return
    except anthropic.APIStatusError as e:
        history.pop()
        log.error("Claude API error %s: %s", e.status_code, e.message)
        await update.message.reply_text("Не получилось получить ответ, попробуй ещё раз.")
        return
    except anthropic.APIConnectionError:
        history.pop()
        log.exception("Нет связи с Claude API")
        await update.message.reply_text("Нет связи с сервером, попробуй ещё раз.")
        return

    history.append({"role": "assistant", "content": answer})
    for part in split_message(answer):
        await update.message.reply_text(part)


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    log.info("Бот запущен, модель %s", MODEL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
