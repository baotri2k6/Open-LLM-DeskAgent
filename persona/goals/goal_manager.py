"""Goal Manager — daily goal selection, tracking, and completion."""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any, Optional

from .daily_goals import pick_daily_goals

try:
    from config.config import WRITABLE_ROOT
    _DATA_PATH = WRITABLE_ROOT / "data" / "daily_goals.json"
except Exception:
    _DATA_PATH = Path("data") / "daily_goals.json"


class GoalManager:
    """
    Manages the companion's daily internal goals.

    Goals are refreshed each calendar day and tracked for completion.
    Completion of goals contributes to mood and relationship score.
    """

    def __init__(self, data_path: Optional[Path] = None) -> None:
        self._path = data_path or _DATA_PATH
        self._data = self._load()
        self._ensure_today()

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def today_goals(self) -> list[dict]:
        """Return today's goals with completion status."""
        return self._data.get("goals", [])

    @property
    def completed_today(self) -> list[dict]:
        return [g for g in self.today_goals if g.get("completed")]

    @property
    def pending_today(self) -> list[dict]:
        return [g for g in self.today_goals if not g.get("completed")]

    @property
    def all_done(self) -> bool:
        return len(self.pending_today) == 0

    def complete_goal(self, goal_id: str) -> bool:
        """
        Mark a goal as completed.
        Returns True if the goal was found and marked.
        """
        for g in self._data.get("goals", []):
            if g["id"] == goal_id and not g.get("completed"):
                g["completed"] = True
                g["completed_at"] = time.time()
                self._save()
                return True
        return False

    def try_complete_by_trigger(self, trigger: str) -> list[str]:
        """
        Try to auto-complete goals matching a trigger type.
        Returns list of completed goal IDs.
        """
        completed_ids: list[str] = []
        for g in self.pending_today:
            if g.get("trigger") == trigger:
                if self.complete_goal(g["id"]):
                    completed_ids.append(g["id"])
                    break  # only complete one per trigger per call
        return completed_ids

    def get_prompt_hint(self) -> str:
        """
        Return a one-line hint about pending goals for system prompt injection.
        Helps the companion naturally steer conversations toward goal completion.
        """
        pending = self.pending_today
        if not pending:
            return ""
        goal = pending[0]
        return f"[Mục tiêu hôm nay: {goal['text_vi']}]"

    def snapshot(self) -> dict[str, Any]:
        return {
            "date":            self._data.get("date"),
            "total":           len(self.today_goals),
            "completed":       len(self.completed_today),
            "pending":         [g["id"] for g in self.pending_today],
        }

    # ── Internal ───────────────────────────────────────────────────────────

    def _ensure_today(self) -> None:
        """Refresh goals if it's a new day."""
        today_str = str(date.today())
        if self._data.get("date") != today_str:
            # Use date as seed for reproducible selection per day
            seed = int(today_str.replace("-", ""))
            goals = pick_daily_goals(n=3, seed=seed)
            for g in goals:
                g["completed"] = False
                g.pop("weight", None)
            self._data = {"date": today_str, "goals": goals}
            self._save()

    def _load(self) -> dict:
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# ── Global singleton ───────────────────────────────────────────────────────────
goal_manager = GoalManager()
