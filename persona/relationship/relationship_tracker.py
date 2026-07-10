"""Relationship Tracker — manages relationship score between companion and user."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Optional

from .relationship_levels import (
    INTERACTION_POINTS,
    LEVELS,
    score_to_level,
    get_perks,
)

try:
    from config.config import WRITABLE_ROOT
    _PROFILE_PATH = WRITABLE_ROOT / "data" / "user_profile.json"
except Exception:
    _PROFILE_PATH = Path("data") / "user_profile.json"


class RelationshipTracker:
    """
    Tracks and persists the relationship score between the companion and user.

    Score → Level:
        0–99    → Người lạ    (Stranger)
        100–499 → Người quen  (Acquaintance)
        500+    → Bạn thân    (Close Friend)
    """

    def __init__(self, profile_path: Optional[Path] = None) -> None:
        self._path  = profile_path or _PROFILE_PATH
        self._lock  = threading.Lock()
        self._inside_jokes: list[str] = []
        self._shared_experiences: int = 0
        self._score = self._load_data()

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def score(self) -> int:
        return self._score

    def get_relationship_points(self) -> int:
        """Backward-compatible accessor for evolution modules."""
        return self._score

    @property
    def level(self) -> str:
        """Current relationship level label (Vietnamese)."""
        return score_to_level(self._score)

    @property
    def level_index(self) -> int:
        """0-based index into LEVELS list."""
        return LEVELS.index(self.level) if self.level in LEVELS else 0

    @property
    def perks(self) -> list[str]:
        """Unlocked perks at current level."""
        return get_perks(self.level)

    def add_inside_joke(self, joke: str) -> None:
        """Thêm một inside joke giữa companion và user."""
        with self._lock:
            if joke not in self._inside_jokes:
                self._inside_jokes.append(joke)
        self._save()

    def get_inside_jokes(self) -> list[str]:
        """Lấy danh sách các inside jokes."""
        return self._inside_jokes

    def add_shared_experience(self) -> None:
        """Tăng số lượng trải nghiệm chung chia sẻ."""
        with self._lock:
            self._shared_experiences += 1
        self._save()

    def get_shared_experiences(self) -> int:
        """Lấy số lượng trải nghiệm chung."""
        return self._shared_experiences

    def add_points(self, interaction: str = "chat_turn") -> int:
        """
        Add points for an interaction type.
        Returns new score.
        """
        points = INTERACTION_POINTS.get(interaction, 0)
        with self._lock:
            self._score = max(0, self._score + points)
        self._save()
        return self._score

    def add_raw(self, delta: int) -> int:
        """Add raw point delta (positive or negative). Returns new score."""
        with self._lock:
            self._score = max(0, self._score + delta)
        self._save()
        return self._score

    def did_level_up(self, old_level: str) -> bool:
        """Check if score crossed into a new level since old_level."""
        return LEVELS.index(self.level) > LEVELS.index(old_level) if old_level in LEVELS else False

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable snapshot."""
        return {
            "score":       self._score,
            "level":       self.level,
            "level_index": self.level_index,
            "perks":       self.perks,
            "inside_jokes": self._inside_jokes,
            "shared_experiences": self._shared_experiences
        }

    # ── Persistence ────────────────────────────────────────────────────────

    def _load_data(self) -> int:
        """Load relationship data from user profile JSON."""
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                rel = data.get("relationship", {})
                if isinstance(rel, dict):
                    self._inside_jokes = list(rel.get("inside_jokes", []))
                    self._shared_experiences = int(rel.get("shared_experiences", 0))
                    return int(rel.get("score", 0))
                # Legacy: MemoryService stored relationship as a dict with 'score' key
                self._inside_jokes = []
                self._shared_experiences = 0
                return int(data.get("relationship_score", 0))
        except Exception:
            pass
        self._inside_jokes = []
        self._shared_experiences = 0
        return 0

    def _save(self) -> None:
        """Persist data to user profile JSON."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            existing: dict = {}
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.setdefault("relationship", {})
            existing["relationship"]["score"] = self._score
            existing["relationship"]["level"] = self.level
            existing["relationship"]["inside_jokes"] = self._inside_jokes
            existing["relationship"]["shared_experiences"] = self._shared_experiences
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception:
            pass



# ── Global singleton ───────────────────────────────────────────────────────────
relationship_tracker = RelationshipTracker()
