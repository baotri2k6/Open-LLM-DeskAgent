"""
Fallback emotion detector dùng roberta-base-go_emotions.
Chỉ load model khi cần — lazy singleton.

Port từ J.A.I.son pattern: detect emotion trực tiếp từ text output của LLM,
không phụ thuộc vào việc LLM có format [emotion:...] tag đúng hay không.
"""
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# Map 28 go_emotions labels → DeskAgent emotion strings
ROBERTA_TO_EMOTION = {
    "joy":             "happy",
    "amusement":       "happy",
    "excitement":      "excited",
    "love":            "smile",
    "gratitude":       "smile",
    "admiration":      "smile",
    "approval":        "smile",
    "caring":          "friendly",
    "pride":           "smile",
    "optimism":        "smile",
    "relief":          "smile",
    "sadness":         "sad",
    "grief":           "sad",
    "disappointment":  "sad",
    "remorse":         "sad",
    "anger":           "angry",
    "annoyance":       "angry",
    "disgust":         "angry",
    "fear":            "surprised",
    "nervousness":     "surprised",
    "surprise":        "surprised",
    "confusion":       "thinking",
    "curiosity":       "thinking",
    "realization":     "thinking",
    "embarrassment":   "shy",
    "desire":          "smile",
    "neutral":         "normal",
    "disapproval":     "angry",
}

_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _classifier = pipeline(
                task="text-classification",
                model="SamLowe/roberta-base-go_emotions",
                top_k=1,
                device=device
            )
            logger.info("[EmotionRoberta] Model loaded on %s", device)
        except Exception as e:
            logger.warning("[EmotionRoberta] Failed to load model: %s", e)
            _classifier = False  # Đánh dấu failed, không thử lại
    return _classifier if _classifier else None


def detect_emotion(text: str, min_score: float = 0.4) -> str | None:
    """
    Detect emotion từ text. Trả về DeskAgent emotion string hoặc None nếu không đủ confident.

    Args:
        text: Text cần detect (nên là response đã clean, không có tag)
        min_score: Ngưỡng confidence tối thiểu (0.0–1.0). Dưới ngưỡng → trả về None

    Returns:
        Emotion string ("happy", "sad", "angry", "surprised", "thinking", "normal", ...) hoặc None
    """
    if not text or len(text.strip()) < 5:
        return None

    classifier = _get_classifier()
    if classifier is None:
        return None

    try:
        result = classifier(text[:512])[0][0]  # Giới hạn 512 chars
        label = result["label"]
        score = result["score"]

        if score < min_score:
            return None

        mapped = ROBERTA_TO_EMOTION.get(label, "normal")
        logger.debug("[EmotionRoberta] %s → %s (%.2f)", label, mapped, score)
        return mapped
    except Exception as e:
        logger.warning("[EmotionRoberta] Inference failed: %s", e)
        return None


def preload():
    """Preload model ở startup để tránh latency lần đầu."""
    _get_classifier()
