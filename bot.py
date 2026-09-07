"""
Single entry point for the whole project. Run this one file and every
feature (chat, document Q&A, recommendations, email assistant) is
available as Telegram bot commands.
"""
import os
import logging

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters,
)

import ai_provider
from modules import document_qa, recommender, email_assistant

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", 10))

# {user_id: [{"role": ..., "content": ...}, ...]}
_chat_histories = {}

CHAT_SYSTEM_PROMPT = (
    "You are a helpful, friendly AI assistant chatting with a user on Telegram. "
    "Keep replies conversational and not overly long unless the user asks for detail."
)


# ---------- /start and help ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Hi! I'm your all-in-one AI assistant. Here's what I can do:\n\n"
        "💬 *Just type a message* — chat with me normally.\n\n"
        "📄 *Send me a .txt or .pdf file* — then use /askdoc <question> to ask "
        "questions about it.\n\n"
        "🎯 /recommend <category> | <preferences> — e.g.\n"
        "`/recommend movies | feel-good comedy under 2 hours`\n\n"
        "📧 /email_summary — summarize your unread Gmail (needs one-time setup, see README)\n"
        "📧 /email_draft <instructions> — draft a reply to your latest unread email\n\n"
        "/reset — clear our chat history"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _chat_histories.pop(update.effective_user.id, None)
    document_qa.clear_document(update.effective_user.id)
    await update.message.reply_text("Cleared our chat history and any uploaded document.")


# ---------- general chat ----------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    history = _chat_histories.setdefault(user_id, [])
    history.append({"role": "user", "content": user_text})
    history[:] = history[-MAX_HISTORY_TURNS * 2:]  # keep it bounded

    await update.message.chat.send_action("typing")
    reply = ai_provider.ask_ai(CHAT_SYSTEM_PROMPT, history)
    history.append({"role": "assistant", "content": reply})

    await update.message.reply_text(reply)


# ---------- document Q&A ----------

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document
    filename = doc.file_name

    if not (filename.lower().endswith(".txt") or filename.lower().endswith(".pdf")):
        await update.message.reply_text("Please send a .txt or .pdf file.")
        return

    await update.message.reply_text("Reading your document...")
    file = await doc.get_file()
    local_path = os.path.join("data", f"{user_id}_{filename}")
    os.makedirs("data", exist_ok=True)
    await file.download_to_drive(local_path)

    num_chunks = document_qa.load_document(user_id, local_path, filename)
    await update.message.reply_text(
        f"Loaded \"{filename}\" ({num_chunks} sections). "
        f"Now ask me about it with /askdoc <your question>."
    )


async def askdoc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("Usage: /askdoc <your question>")
        return

    await update.message.chat.send_action("typing")
    answer = document_qa.answer_question(user_id, question)
    await update.message.reply_text(answer)


# ---------- recommendations ----------

async def recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = " ".join(context.args)
    if "|" not in raw:
        await update.message.reply_text(
            "Usage: /recommend <category> | <preferences>\n"
            "Example: /recommend movies | feel-good comedy under 2 hours"
        )
        return

    category, preferences = raw.split("|", 1)
    await update.message.chat.send_action("typing")
    result = recommender.get_recommendations(category.strip(), preferences.strip())
    await update.message.reply_text(result, parse_mode="Markdown")


# ---------- email assistant ----------

async def email_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking your inbox...")
    try:
        summary = email_assistant.get_unread_summary()
        await update.message.reply_text(summary)
    except FileNotFoundError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"Couldn't fetch email: {e}")


async def email_draft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instructions = " ".join(context.args)
    if not instructions:
        await update.message.reply_text("Usage: /email_draft <instructions>, e.g. /email_draft politely decline")
        return

    await update.message.reply_text("Drafting a reply...")
    try:
        result = email_assistant.draft_reply_to_latest(instructions)
        await update.message.reply_text(result)
    except FileNotFoundError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"Couldn't draft reply: {e}")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise EnvironmentError("Set TELEGRAM_BOT_TOKEN in your .env file first.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("askdoc", askdoc))
    app.add_handler(CommandHandler("recommend", recommend))
    app.add_handler(CommandHandler("email_summary", email_summary))
    app.add_handler(CommandHandler("email_draft", email_draft))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
