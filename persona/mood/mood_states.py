"""MoodState dataclass — dynamic psychological states of the companion."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ── Mood labels ────────────────────────────────────────────────────────────────

MOOD_LABELS = [
    "vui vẻ",     # happy / cheerful  (default)
    "tập trung",  # focused / in-the-zone
    "suy nghĩ",   # thoughtful / pensive
    "tò mò",      # curious / intrigued
    "buồn bã",    # sad / melancholic
    "giận dỗi",   # peeved / annoyed
    "mơ màng",    # dreamy / spaced out
    "phấn khích", # excited / hyped
    "mệt mỏi",   # tired / low energy
    "chán",       # bored / restless
]

MOOD_EN_MAP: dict[str, str] = {
    "vui vẻ":     "happy",
    "tập trung":  "focused",
    "suy nghĩ":   "thoughtful",
    "tò mò":      "curious",
    "buồn bã":    "sad",
    "giận dỗi":   "annoyed",
    "mơ màng":    "dreamy",
    "phấn khích": "excited",
    "mệt mỏi":   "tired",
    "chán":       "bored",
}


@dataclass
class MoodState:
    """
    Dynamic psychological state of the companion.

    All float attributes range from 0.0 (low) to 1.0 (high).
    `mood` is a string label from MOOD_LABELS.
    """

    # Dynamic states
    energy:     float = 0.7   # vitality / liveliness
    focus:      float = 0.5   # concentration level
    curiosity:  float = 0.6   # desire to explore / ask questions
    confidence: float = 0.7   # self-assuredness
    stress:     float = 0.1   # tension / pressure

    # Mood label
    mood: str = "vui vẻ"

    # Timestamps (monotonic seconds)
    last_updated: float = field(default_factory=time.monotonic)

    # ── Computed ───────────────────────────────────────────────────────────

    @property
    def mood_en(self) -> str:
        """English equivalent of the mood label."""
        return MOOD_EN_MAP.get(self.mood, self.mood)

    @property
    def is_energized(self) -> bool:
        return self.energy >= 0.6

    @property
    def is_focused(self) -> bool:
        return self.focus >= 0.65

    @property
    def is_stressed(self) -> bool:
        return self.stress >= 0.6

    @property
    def overall_wellbeing(self) -> float:
        """Composite wellbeing score (0.0–1.0)."""
        return round(
            (self.energy * 0.3 + self.confidence * 0.25 + (1 - self.stress) * 0.25 + self.focus * 0.2),
            2,
        )

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "energy":       round(self.energy, 2),
            "focus":        round(self.focus, 2),
            "curiosity":    round(self.curiosity, 2),
            "confidence":   round(self.confidence, 2),
            "stress":       round(self.stress, 2),
            "mood":         self.mood,
            "mood_en":      self.mood_en,
            "wellbeing":    self.overall_wellbeing,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MoodState":
        return cls(
            energy=float(data.get("energy", 0.7)),
            focus=float(data.get("focus", 0.5)),
            curiosity=float(data.get("curiosity", 0.6)),
            confidence=float(data.get("confidence", 0.7)),
            stress=float(data.get("stress", 0.1)),
            mood=data.get("mood", "vui vẻ"),
        )

    @classmethod
    def default(cls) -> "MoodState":
        return cls()

    def __repr__(self) -> str:
        return (
            f"<MoodState mood={self.mood!r} energy={self.energy:.1f} "
            f"focus={self.focus:.1f} curiosity={self.curiosity:.1f} "
            f"stress={self.stress:.1f}>"
        )
