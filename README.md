# All-in-One AI Assistant (Telegram Bot)

One bot, one command to run, four features:
- 💬 General AI chat
- 📄 Document Q&A (upload a .txt/.pdf, ask questions about it)
- 🎯 AI recommendations (movies, books, restaurants, anything)
- 📧 Gmail assistant (summarize unread mail, draft replies)

Runs entirely on free tiers: Telegram (free), Groq or Google Gemini (free LLM),
Gmail API (free). No Twilio, no ngrok, no phone numbers needed.

## Setup

### 1. Install dependencies
```bash
python -m venv venv
venv\Scripts\activate          (Windows)
source venv/bin/activate       (Mac/Linux)
pip install -r requirements.txt
```

### 2. Create your Telegram bot (free, ~1 minute)
1. Open Telegram, search for **@BotFather**, start a chat.
2. Send `/newbot`, follow the prompts (give it a name and a username ending in "bot").
3. BotFather gives you a token like `123456:ABC-DEF...` — copy it.

### 3. Get a free LLM key
- **Groq** (default, recommended): console.groq.com/keys
- **Google Gemini** (alternative): aistudio.google.com/apikey

### 4. Configure environment
```bash
cp .env.example .env
```
Fill in `TELEGRAM_BOT_TOKEN`, set `LLM_PROVIDER` (groq or google), and the
matching API key.

### 5. Run it

**Telegram bot:**
```bash
python bot.py
```
Leave this running. Open Telegram, find your bot by the username you gave
it, and send `/start`.

**Website** (same features, browser interface — can run at the same time
as the bot, they share the same backend modules):
```bash
python app.py
```
Then open **http://localhost:5050** in your browser. No Telegram needed
for this version — just use the buttons and text boxes on the page.

That's it for chat, document Q&A, and recommendations — they work immediately
on both.

## Using each feature

**Chat**: just type normally.

**Document Q&A**: send a `.txt` or `.pdf` file directly in the chat, then:
```
/askdoc What are the main points in section 2?
```

**Recommendations**:
```
/recommend movies | feel-good comedy under 2 hours
/recommend restaurants | budget-friendly Italian, vegetarian options
```

**Reset conversation/document**:
```
/reset
```

## Email Assistant setup (optional — takes a few extra minutes)

This feature needs its own one-time setup since it accesses your real Gmail:

1. Go to console.cloud.google.com, create a new project (or use an existing one).
2. Go to **APIs & Services → Library**, search "Gmail API", click **Enable**.
3. Go to **APIs & Services → OAuth consent screen**. Choose "External", fill
   in the required fields (app name, your email), and add yourself as a
   test user.
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
   Choose **Desktop app** as the type.
5. Download the resulting JSON file, rename it to `credentials.json`, and
   place it in this project's `credentials/` folder.
6. Run the bot and use `/email_summary` for the first time — it'll open a
   browser window asking you to log in and approve access. After that, it's
   saved and won't ask again.

Usage:
```
/email_summary
/email_draft politely decline and suggest next week instead
```

`/email_draft` creates a draft in your Gmail — it never sends anything
automatically. Review and hit send yourself from Gmail.

## Notes

- Chat history and uploaded documents are stored in memory per Telegram
  user — restarting the bot clears them. For persistence across restarts,
  swap the in-memory dicts in `bot.py` and `modules/document_qa.py` for a
  simple database.
- Recommendations come from the LLM's own knowledge, not a live database —
  good for general suggestions, but double-check anything time-sensitive
  (hours, availability, current pricing).
