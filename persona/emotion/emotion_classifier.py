"""Keyword-based emotion classifier — no ML model needed, fast and lightweight."""

from __future__ import annotations

import re
from typing import Optional

# ── Keyword rules ─────────────────────────────────────────────────────────────
# Ordered from most specific to least specific.
# Each entry: (emotion_label, [trigger_keywords])

_RULES: list[tuple[str, list[str]]] = [
    # Positive
    ("excited",   ["tuyệt vời", "thích quá", "wow", "amazing", "awesome", "yayyy", "yay", "phê", "đỉnh", "hype", "excited"]),
    ("happy",     ["vui", "hay quá", "thú vị", "cảm ơn", "hihi", "hehe", "haha", "😊", "😁", "great", "wonderful", "love", "thích"]),
    ("playful",   ["trêu", "đùa", "haha", "lol", "😜", "😝", "playful", "teasing", "nghịch"]),
    ("proud",     ["tự hào", "làm được rồi", "xong rồi", "hoàn thành", "done", "completed", "proud", "achievement"]),
    ("curious",   ["tại sao", "làm thế nào", "how", "why", "what is", "giải thích", "thật không", "really?", "curious", "tò mò", "interesting"]),
    ("surprised", ["ồ", "ôi", "whoa", "wow", "bất ngờ", "không ngờ", "seriously", "omg", "oh no", "unexpected"]),
    ("loving",    ["yêu", "thương", "love", "❤️", "💕", "🥰", "quý", "nhớ", "thân thương"]),

    # Negative
    ("sad",       ["buồn", "tệ quá", "chán", "sad", "unhappy", "😢", "😭", "không vui", "thất vọng", "nản"]),
    ("angry",     ["tức", "giận", "bực", "khó chịu", "angry", "mad", "😠", "😤", "ugh", "ridiculous"]),
    ("scared",    ["sợ", "lo lắng", "lo", "afraid", "scared", "anxious", "worried", "😰", "😨"]),
    ("tired",     ["mệt", "buồn ngủ", "exhausted", "tired", "sleepy", "😴", "zzz", "kiệt sức"]),
    ("confused",  ["không hiểu", "confused", "hả?", "huh?", "what?", "lạ thật", "😕", "🤔"]),
    ("bored",     ["chán", "nhàm", "boring", "bored", "meh", "whatever", "😑"]),

    # Neutral / thinking
    ("thinking",  ["hmm", "để xem", "thú vị đó", "chờ chút", "thật ra", "technically", "🤔", "💭", "theo như"]),
    ("neutral",   []),   # fallback — always matches
]

_COMPILED: list[tuple[str, list[re.Pattern]]] = [
    (emotion, [re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords])
    for emotion, keywords in _RULES
]


def classify_emotion(text: str, default: str = "neutral") -> tuple[str, float]:
    """
    Classify the emotion expressed in *text*.

    Returns:
        (emotion_label, confidence_score)  — confidence is 0.0–1.0.
    """
    if not text or not text.strip():
        return default, 0.0

    scores: dict[str, int] = {}
    for emotion, patterns in _COMPILED:
        if emotion == "neutral":
            continue
        count = sum(1 for p in patterns if p.search(text))
        if count:
            scores[emotion] = count

    if not scores:
        return default, 0.0

    best = max(scores, key=lambda e: scores[e])
    total_hits = sum(scores.values())
    confidence = min(1.0, scores[best] / max(1, total_hits) + 0.2 * scores[best])
    return best, round(min(1.0, confidence), 2)


def classify_emotion_from_response(ai_text: str) -> Optional[str]:
    """
    Detect emotion from AI's own response text (not user input).
    Returns emotion label or None if no strong signal found.
    """
    emotion, confidence = classify_emotion(ai_text)
    if emotion == "neutral" or confidence < 0.2:
        return None
    return emotion
