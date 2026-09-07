"""
Web version of the same assistant the Telegram bot provides — same brain,
different front door. Run this alongside or instead of bot.py.
"""
import os
import uuid

from flask import Flask, request, jsonify, session, render_template

import ai_provider
from modules import document_qa, recommender, email_assistant

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", 10))

# {session_id: [{"role":..., "content":...}, ...]}
_chat_histories = {}

CHAT_SYSTEM_PROMPT = (
    "You are a helpful, friendly AI assistant talking to a user through a web chat. "
    "Keep replies conversational and not overly long unless the user asks for detail."
)


def _get_session_id():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    sid = _get_session_id()
    user_text = request.json.get("message", "").strip()
    if not user_text:
        return jsonify({"error": "Empty message"}), 400

    history = _chat_histories.setdefault(sid, [])
    history.append({"role": "user", "content": user_text})
    history[:] = history[-MAX_HISTORY_TURNS * 2:]

    reply = ai_provider.ask_ai(CHAT_SYSTEM_PROMPT, history)
    history.append({"role": "assistant", "content": reply})

    return jsonify({"reply": reply})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    sid = _get_session_id()
    _chat_histories.pop(sid, None)
    document_qa.clear_document(sid)
    return jsonify({"status": "cleared"})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    sid = _get_session_id()
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400

    filename = file.filename
    if not (filename.lower().endswith(".txt") or filename.lower().endswith(".pdf")):
        return jsonify({"error": "Only .txt and .pdf files are supported"}), 400

    os.makedirs("data", exist_ok=True)
    local_path = os.path.join("data", f"{sid}_{filename}")
    file.save(local_path)

    num_chunks = document_qa.load_document(sid, local_path, filename)
    return jsonify({"filename": filename, "chunks": num_chunks})


@app.route("/api/askdoc", methods=["POST"])
def api_askdoc():
    sid = _get_session_id()
    question = request.json.get("question", "").strip()
    if not question:
        return jsonify({"error": "Empty question"}), 400

    answer = document_qa.answer_question(sid, question)
    return jsonify({"answer": answer, "filename": document_qa.get_filename(sid)})


@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    category = request.json.get("category", "").strip()
    preferences = request.json.get("preferences", "").strip()
    if not category or not preferences:
        return jsonify({"error": "Category and preferences are both required"}), 400

    result = recommender.get_recommendations(category, preferences)
    return jsonify({"result": result})


@app.route("/api/email/summary", methods=["POST"])
def api_email_summary():
    try:
        summary = email_assistant.get_unread_summary()
        return jsonify({"summary": summary})
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Couldn't fetch email: {e}"}), 500


@app.route("/api/email/draft", methods=["POST"])
def api_email_draft():
    instructions = request.json.get("instructions", "").strip()
    if not instructions:
        return jsonify({"error": "Instructions are required"}), 400
    try:
        result = email_assistant.draft_reply_to_latest(instructions)
        return jsonify({"result": result})
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Couldn't draft reply: {e}"}), 500


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    port = int(os.getenv("WEB_PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False)
