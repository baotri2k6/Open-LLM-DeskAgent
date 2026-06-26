"""Emotion → Live2D expression + motion mapping."""

from __future__ import annotations

# ── Expression map ────────────────────────────────────────────────────────────
# Maps emotion labels to Live2D expression file names.
# These must match the expression names defined in the model's .model3.json

EXPRESSION_MAP: dict[str, str] = {
    # Positive
    "happy":     "exp_happy",
    "excited":   "exp_excited",
    "playful":   "exp_playful",
    "proud":     "exp_happy",
    "loving":    "exp_loving",
    "surprised": "exp_surprised",
    "curious":   "exp_curious",

    # Neutral / thinking
    "neutral":   "exp_neutral",
    "thinking":  "exp_thinking",
    "confused":  "exp_confused",

    # Negative
    "sad":       "exp_sad",
    "angry":     "exp_angry",
    "scared":    "exp_scared",
    "tired":     "exp_tired",
    "bored":     "exp_bored",
}

# ── Motion map ────────────────────────────────────────────────────────────────
# Maps emotion labels to suggested Live2D motion group names.

MOTION_MAP: dict[str, str] = {
    "happy":     "motion_happy",
    "excited":   "motion_excited",
    "playful":   "motion_idle",
    "proud":     "motion_happy",
    "loving":    "motion_idle",
    "surprised": "motion_surprised",
    "curious":   "motion_curious",
    "neutral":   "motion_idle",
    "thinking":  "motion_thinking",
    "confused":  "motion_idle",
    "sad":       "motion_sad",
    "angry":     "motion_angry",
    "scared":    "motion_idle",
    "tired":     "motion_idle",
    "bored":     "motion_idle",
}

_FALLBACK_EXPRESSION = "exp_neutral"
_FALLBACK_MOTION = "motion_idle"


def get_expression(emotion: str) -> str:
    """Return the Live2D expression name for an emotion label."""
    return EXPRESSION_MAP.get(emotion, _FALLBACK_EXPRESSION)


def get_motion(emotion: str) -> str:
    """Return the Live2D motion group for an emotion label."""
    return MOTION_MAP.get(emotion, _FALLBACK_MOTION)


def get_avatar_hints(emotion: str) -> dict[str, str]:
    """Return a complete avatar hint dict for use in API responses."""
    return {
        "emotion":    emotion,
        "expression": get_expression(emotion),
        "motion":     get_motion(emotion),
    }


def list_emotions() -> list[str]:
    """Return all supported emotion labels."""
    return list(EXPRESSION_MAP.keys())