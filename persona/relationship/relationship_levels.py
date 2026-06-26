"""Relationship level definitions and thresholds."""

from __future__ import annotations

# ── Level labels (Vietnamese) ──────────────────────────────────────────────────
LEVELS = ["Người lạ", "Người quen", "Bạn thân"]

# Score thresholds: (min_score, max_score_exclusive)
THRESHOLDS: dict[str, tuple[int, float]] = {
    "Người lạ":   (0,   100),
    "Người quen": (100, 500),
    "Bạn thân":   (500, float("inf")),
}

# Points earned per interaction type
INTERACTION_POINTS: dict[str, int] = {
    "chat_turn":          2,    # regular conversation turn
    "long_conversation":  5,    # 10+ message session
    "task_completed":     8,    # user asked for task, agent succeeded
    "compliment":        10,    # user said something positive
    "shared_secret":     15,    # user shared personal info
    "conflict":          -5,    # user seemed upset/angry
    "ignored":           -2,    # user left without saying bye
}

# Unlock perks per level
LEVEL_PERKS: dict[str, list[str]] = {
    "Người lạ": [
        "Basic conversation",
        "Formal speech style",
    ],
    "Người quen": [
        "Casual speech style",
        "Nickname usage",
        "Personal topic discussions",
        "Proactive check-ins",
    ],
    "Bạn thân": [
        "Intimate speech style",
        "Teasing / playful banter",
        "Sharing opinions freely",
        "Deep personal conversations",
        "Inside jokes",
    ],
}


def score_to_level(score: int) -> str:
    """Convert a numeric score to a relationship level label."""
    for level, (lo, hi) in THRESHOLDS.items():
        if lo <= score < hi:
            return level
    return "Bạn thân"


def level_to_score_range(level: str) -> tuple[int, float]:
    """Return (min, max) score range for a level."""
    return THRESHOLDS.get(level, (0, 100))


def get_perks(level: str) -> list[str]:
    """Return unlocked perks for a relationship level."""
    unlocked: list[str] = []
    for lvl in LEVELS:
        unlocked.extend(LEVEL_PERKS.get(lvl, []))
        if lvl == level:
            break
    return unlocked
