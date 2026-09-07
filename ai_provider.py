"""
One shared interface so every module (chat, doc Q&A, recommender, email)
can call ask_ai() without caring whether Groq or Gemini is configured.
"""
import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

if LLM_PROVIDER == "groq":
    from groq import Groq
    _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    _model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
elif LLM_PROVIDER == "google":
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    _gemini = genai.GenerativeModel(os.getenv("GOOGLE_MODEL", "gemini-1.5-flash"))
else:
    raise EnvironmentError('LLM_PROVIDER must be "groq" or "google"')


def ask_ai(system_prompt: str, history: list) -> str:
    """
    history: list of {"role": "user"|"assistant", "content": str}, at least one item.
    Returns the AI's reply text.
    """
    if LLM_PROVIDER == "groq":
        messages = [{"role": "system", "content": system_prompt}] + history
        resp = _client.chat.completions.create(
            model=_model,
            max_tokens=600,
            messages=messages,
        )
        return resp.choices[0].message.content.strip()
    else:
        gemini_history = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [m["content"]]}
            for m in history[:-1]
        ]
        chat = _gemini.start_chat(history=gemini_history)
        full_prompt = f"{system_prompt}\n\nUser: {history[-1]['content']}"
        resp = chat.send_message(full_prompt)
        return resp.text.strip()


def ask_ai_simple(system_prompt: str, user_message: str) -> str:
    """Convenience wrapper for one-off prompts with no conversation history."""
    return ask_ai(system_prompt, [{"role": "user", "content": user_message}])
