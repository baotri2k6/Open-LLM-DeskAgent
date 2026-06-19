"""Emotion Engine — phân tích cảm xúc từ text người dùng."""
from __future__ import annotations
import re

_POSITIVE = re.compile(
    r"(cảm ơn|tuyệt|hay|giỏi|ngon|thích|vui|ổn|được|tốt|haha|hihi|ok|oke|love|❤|😊|😄|😍)",
    re.IGNORECASE,
)
_NEGATIVE = re.compile(
    r"(buồn|chán|tệ|dở|ghét|khó chịu|mệt|tức|giận|sai|lỗi|fail|😭|😠|😡|💢)",
    re.IGNORECASE,
)
_QUESTION = re.compile(r"\?|không biết|tại sao|vì sao|như thế nào|là gì", re.IGNORECASE)


def detect_emotion(text: str) -> str:
    """Trả về emotion string từ text người dùng."""
    if not text:
        return "neutral"
    if _POSITIVE.search(text):
        return "happy"
    if _NEGATIVE.search(text):
        return "sad"
    if _QUESTION.search(text):
        return "thinking"
    return "neutral"