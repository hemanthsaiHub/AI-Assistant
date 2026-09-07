"""
Gmail integration using Google's official API (free, no cost).
Requires a one-time OAuth setup — see README section on Email Assistant.

Scopes used:
- gmail.readonly (to read unread emails)
- gmail.compose (to create draft replies — does NOT send anything automatically)
"""
import os
import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import ai_provider

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

CREDENTIALS_PATH = os.path.join("credentials", "credentials.json")
TOKEN_PATH = os.path.join("credentials", "token.json")


def _get_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Missing {CREDENTIALS_PATH}. See README's Email Assistant "
                    f"setup section to download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            # This opens a browser window ONCE for you to approve access.
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _get_unread_messages(max_results=5):
    service = _get_service()
    results = service.users().messages().list(
        userId="me", labelIds=["UNREAD", "INBOX"], maxResults=max_results
    ).execute()
    messages = results.get("messages", [])

    full_messages = []
    for msg in messages:
        full = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        full_messages.append(full)
    return full_messages


def _extract_subject_and_snippet(message: dict) -> dict:
    headers = message.get("payload", {}).get("headers", [])
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(no subject)")
    sender = next((h["value"] for h in headers if h["name"] == "From"), "(unknown sender)")
    snippet = message.get("snippet", "")
    return {"id": message["id"], "subject": subject, "from": sender, "snippet": snippet}


def get_unread_summary(max_results=5) -> str:
    messages = _get_unread_messages(max_results)
    if not messages:
        return "No unread emails right now."

    parsed = [_extract_subject_and_snippet(m) for m in messages]
    listing = "\n".join(
        f"- From: {p['from']} | Subject: {p['subject']} | Preview: {p['snippet']}"
        for p in parsed
    )

    system_prompt = (
        "Summarize this list of unread emails for the user in a short, scannable way. "
        "Group similar ones if relevant, and flag anything that looks urgent or time-sensitive."
    )
    return ai_provider.ask_ai_simple(system_prompt, listing)


def draft_reply_to_latest(instructions: str) -> str:
    """
    Drafts (but does NOT send) a reply to the most recent unread email,
    based on the user's instructions. Returns the draft text for review.
    """
    messages = _get_unread_messages(max_results=1)
    if not messages:
        return "No unread emails to reply to."

    latest = _extract_subject_and_snippet(messages[0])
    system_prompt = (
        f"Draft a reply to this email:\n"
        f"From: {latest['from']}\nSubject: {latest['subject']}\nPreview: {latest['snippet']}\n\n"
        f"Follow these instructions for the reply: {instructions}\n\n"
        f"Write ONLY the reply body text, no subject line, no signature placeholder."
    )
    draft_text = ai_provider.ask_ai_simple(system_prompt, instructions)

    # Actually create it as a Gmail draft (not sent) so the user can review/edit/send themselves.
    service = _get_service()
    message = MIMEText(draft_text)
    message["to"] = latest["from"]
    message["subject"] = f"Re: {latest['subject']}"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()

    return f"Draft created in your Gmail Drafts folder:\n\n{draft_text}"
