"""
Lightweight document Q&A: no vector database needed.
- Splits uploaded text into chunks
- Uses TF-IDF + cosine similarity to find the most relevant chunks for a question
- Feeds those chunks to the LLM as context
Stored per-user (by Telegram user id) in memory, so restarting the bot clears documents.
"""
import os
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import ai_provider

# {user_id: {"chunks": [str, ...], "filename": str}}
_user_docs = {}

CHUNK_SIZE = 800  # characters per chunk
CHUNK_OVERLAP = 100
TOP_K = 4  # how many chunks to feed the LLM per question


def extract_text_from_file(filepath: str) -> str:
    if filepath.lower().endswith(".pdf"):
        reader = PdfReader(filepath)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def _chunk_text(text: str) -> list:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]


def load_document(user_id: int, filepath: str, filename: str) -> int:
    """Extracts, chunks, and stores a document for this user. Returns number of chunks."""
    text = extract_text_from_file(filepath)
    chunks = _chunk_text(text)
    _user_docs[user_id] = {"chunks": chunks, "filename": filename}
    return len(chunks)


def has_document(user_id: int) -> bool:
    return user_id in _user_docs and len(_user_docs[user_id]["chunks"]) > 0


def get_filename(user_id: int) -> str:
    return _user_docs.get(user_id, {}).get("filename", "")


def _top_chunks(user_id: int, question: str) -> list:
    chunks = _user_docs[user_id]["chunks"]
    if len(chunks) <= TOP_K:
        return chunks

    vectorizer = TfidfVectorizer().fit(chunks + [question])
    chunk_vectors = vectorizer.transform(chunks)
    question_vector = vectorizer.transform([question])
    scores = cosine_similarity(question_vector, chunk_vectors)[0]
    ranked_indices = scores.argsort()[::-1][:TOP_K]
    return [chunks[i] for i in sorted(ranked_indices)]


def answer_question(user_id: int, question: str) -> str:
    if not has_document(user_id):
        return "You haven't uploaded a document yet. Send me a .txt or .pdf file first."

    relevant_chunks = _top_chunks(user_id, question)
    context = "\n\n---\n\n".join(relevant_chunks)

    system_prompt = (
        "You answer questions using ONLY the document excerpts provided below. "
        "If the answer isn't in the excerpts, say you don't have enough information "
        "in the document to answer that.\n\n"
        f"DOCUMENT EXCERPTS:\n{context}"
    )
    return ai_provider.ask_ai_simple(system_prompt, question)


def clear_document(user_id: int):
    _user_docs.pop(user_id, None)
