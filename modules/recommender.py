"""
AI-generated recommendations (movies, books, restaurants, products, etc).
No external dataset — relies on the LLM's own knowledge plus whatever
preferences the user gives it. Good enough for general suggestions;
for location-specific/live results (e.g. restaurants open now), an LLM's
knowledge can be outdated, so we say so.
"""
import ai_provider

SYSTEM_PROMPT = """You are a thoughtful recommendation assistant. Given a category and
the user's preferences, suggest 3-5 specific options with a short reason for each.

Format each recommendation as:
1. **Name** — one sentence on why it fits their preferences.

If the request involves anything location-specific, time-specific (e.g. "open now"),
or could have changed recently, mention briefly that your suggestions are based on
general knowledge and the user should double check current availability/hours."""


def get_recommendations(category: str, preferences: str) -> str:
    user_message = f"Category: {category}\nPreferences: {preferences}"
    return ai_provider.ask_ai_simple(SYSTEM_PROMPT, user_message)
