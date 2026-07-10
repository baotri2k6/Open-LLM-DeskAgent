"""Mood Engine — manages dynamic mood state with natural drift and event updates."""

from __future__ import annotations

import json
import random
import threading
import time
from pathlib import Path
from typing import Any, Optional

from .mood_states import MoodState, MOOD_LABELS

try:
    from config.config import WRITABLE_ROOT
    _PROFILE_PATH = WRITABLE_ROOT / "data" / "user_profile.json"
except Exception:
    _PROFILE_PATH = Path("data") / "user_profile.json"

# ── Mood drift config ──────────────────────────────────────────────────────────
_DRIFT_INTERVAL    = 300.0   # seconds between automatic drift ticks
_DRIFT_MAGNITUDE   = 0.04    # max change per drift tick per attribute
_ENERGY_RESET_HOUR = 8       # hour of day when energy resets to high (morning)


class MoodEngine:
    """
    Manages the companion's dynamic mood state.

    Features:
    - Natural random drift over time (simulates personality variation)
    - Event-driven updates (task success, user idle, conversation...)
    - Persistence: reads/writes mood to user_profile.json
    - Thread-safe
    """

    def __init__(self, profile_path: Optional[Path] = None) -> None:
        self._path   = profile_path or _PROFILE_PATH
        self._lock   = threading.Lock()
        self._state  = self._load()
        self._last_drift = time.monotonic()

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def state(self) -> MoodState:
        """Current mood state (applies drift if overdue)."""
        self._maybe_drift()
        return self._state

    def get_mood(self) -> str:
        """Return the current mood label (Vietnamese)."""
        return self.state.mood

    def get_snapshot(self) -> dict[str, Any]:
        """Return a serializable snapshot."""
        return self.state.to_dict()

    def update_from_event(self, event: str) -> MoodState:
        """
        Apply event-driven mood changes.

        Supported events:
            user_arrived, user_left, task_success, task_failed,
            idle_short, idle_long, compliment_received, criticism_received,
            long_conversation, morning_reset
        """
        self._maybe_drift()
        with self._lock:
            s = self._state
            if event == "user_arrived":
                s.energy     = min(1.0, s.energy    + 0.15)
                s.mood       = "vui vẻ"
            elif event == "user_left":
                s.energy     = max(0.0, s.energy    - 0.1)
                s.mood       = "suy nghĩ"
            elif event == "task_success":
                s.confidence = min(1.0, s.confidence + 0.1)
                s.stress     = max(0.0, s.stress     - 0.1)
                s.mood       = "phấn khích"
            elif event == "task_failed":
                s.stress     = min(1.0, s.stress     + 0.15)
                s.confidence = max(0.0, s.confidence - 0.08)
                s.mood       = "suy nghĩ"
            elif event == "idle_short":
                s.energy     = max(0.0, s.energy    - 0.05)
                if s.mood not in ("buồn bã", "mơ màng"):
                    s.mood   = "chán"
            elif event == "idle_long":
                s.energy     = max(0.0, s.energy    - 0.12)
                s.mood       = "buồn bã"
            elif event == "compliment_received":
                s.confidence = min(1.0, s.confidence + 0.12)
                s.mood       = "vui vẻ"
            elif event == "criticism_received":
                s.confidence = max(0.0, s.confidence - 0.1)
                s.stress     = min(1.0, s.stress     + 0.1)
                s.mood       = "giận dỗi"
            elif event == "long_conversation":
                s.energy     = max(0.0, s.energy    - 0.08)
                s.stress     = min(1.0, s.stress     + 0.05)
            elif event == "morning_reset":
                s.energy     = 0.85
                s.stress     = 0.05
                s.mood       = "vui vẻ"
            s.last_updated = time.monotonic()
        self._save()
        return self._state

    def update_mood_label(self, mood: str) -> None:
        """Directly set the mood label (e.g. from LLM sentiment analysis)."""
        if mood in MOOD_LABELS:
            with self._lock:
                self._state.mood = mood
                self._state.last_updated = time.monotonic()
            self._save()

    def inject_activity_modifier(self, activity: str) -> None:
        """
        Adjust states based on user's current activity context.

        Activities: coding, gaming, watching, reading, document, unknown
        """
        mods: dict[str, dict[str, float]] = {
            "coding":    {"focus": +0.15, "stress": +0.05},
            "gaming":    {"energy": +0.1, "stress": -0.05},
            "watching":  {"energy": -0.05, "focus": -0.1},
            "reading":   {"focus": +0.1, "curiosity": +0.08},
            "document":  {"focus": +0.12, "stress": +0.03},
        }
        deltas = mods.get(activity, {})
        with self._lock:
            s = self._state
            for attr, delta in deltas.items():
                cur = getattr(s, attr, 0.5)
                setattr(s, attr, round(max(0.0, min(1.0, cur + delta)), 3))

    def consume_energy_for_screen_scan(self, activity: str = "unknown", changed: bool = True) -> MoodState:
        """Drain a tiny amount of energy for autonomous screen/world scans.

        This wires LifeLoop perception cost into the mood model. Focus-heavy
        activities cost slightly more; passive/unknown scans cost less.
        """
        drain = 0.01 if changed else 0.004
        if activity in {"coding", "terminal_work", "working_document"}:
            drain += 0.004
        elif activity in {"watching_video", "idle", "unknown"}:
            drain *= 0.6

        with self._lock:
            s = self._state
            s.energy = round(max(0.0, s.energy - drain), 3)
            if s.energy < 0.25:
                s.mood = "mệt mỏi"
            s.last_updated = time.monotonic()
        self._save()
        return self._state

    # ── Prompt injection ───────────────────────────────────────────────────

    def to_prompt_block(self) -> str:
        """
        Return a compact text block describing current mood for system prompt injection.
        """
        s = self.state
        energy_word   = "cao" if s.energy > 0.65 else ("trung bình" if s.energy > 0.35 else "thấp")
        stress_word   = "có chút căng thẳng" if s.stress > 0.5 else "bình thường"
        curious_word  = "đang rất tò mò" if s.curiosity > 0.7 else ""

        parts = [f"Tâm trạng: {s.mood}", f"Năng lượng: {energy_word}"]
        if curious_word:
            parts.append(curious_word)
        if s.stress > 0.5:
            parts.append(stress_word)
        return " | ".join(parts)

    # ── Persistence ────────────────────────────────────────────────────────

    def _load(self) -> MoodState:
        """Load persisted mood state from user profile JSON."""
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                mood_data = data.get("mood_state")
                if isinstance(mood_data, dict):
                    return MoodState.from_dict(mood_data)
        except Exception:
            pass
        return MoodState.default()

    def _save(self) -> None:
        """Persist current mood state into user profile JSON."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            existing: dict = {}
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing["mood_state"] = self._state.to_dict()
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ── Drift ──────────────────────────────────────────────────────────────

    def _maybe_drift(self) -> None:
        """Apply a small random drift if enough time has passed."""
        now = time.monotonic()
        if now - self._last_drift < _DRIFT_INTERVAL:
            return
        with self._lock:
            self._apply_drift()
            self._last_drift = now

    def _apply_drift(self) -> None:
        """Small random walk on each state attribute."""
        s = self._state
        for attr in ("energy", "focus", "curiosity", "confidence", "stress"):
            cur   = getattr(s, attr)
            delta = random.uniform(-_DRIFT_MAGNITUDE, _DRIFT_MAGNITUDE)
            # Energy naturally restores toward 0.6 baseline
            if attr == "energy" and cur < 0.6:
                delta += 0.01
            # Stress naturally decreases toward 0.1 baseline
            if attr == "stress" and cur > 0.1:
                delta -= 0.01
            setattr(s, attr, round(max(0.0, min(1.0, cur + delta)), 3))
        # Recalculate mood label from current state
        self._recalculate_mood_label()

    def _recalculate_mood_label(self) -> None:
        """Derive mood label from numeric states."""
        s = self._state
        if s.energy < 0.3:
            s.mood = "mệt mỏi"
        elif s.stress > 0.7:
            s.mood = "giận dỗi"
        elif s.focus > 0.75:
            s.mood = "tập trung"
        elif s.curiosity > 0.75:
            s.mood = "tò mò"
        elif s.energy > 0.8:
            s.mood = "phấn khích"
        elif s.energy > 0.6:
            s.mood = "vui vẻ"
        # If none match, keep existing mood (it was set by an event)


# ── Global singleton ───────────────────────────────────────────────────────────
mood_engine = MoodEngine()
