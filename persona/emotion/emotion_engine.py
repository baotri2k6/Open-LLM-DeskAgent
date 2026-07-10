"""Emotion Engine — real-time emotion state machine with natural decay."""

from __future__ import annotations

import threading
import time
from typing import Optional

from .emotion_classifier import classify_emotion, classify_emotion_from_response
from .emotion_mapper import get_expression, get_motion, get_avatar_hints

# ── Constants ─────────────────────────────────────────────────────────────────
_DEFAULT_EMOTION = "neutral"
_DECAY_INTERVAL  = 120.0   # seconds before emotion fades toward neutral
_MIN_INTENSITY   = 0.1     # intensity floor before snapping to neutral


class EmotionEngine:
    """
    Tracks and manages the companion's current emotional state.

    Design principles:
    - Emotions fade naturally over time (decay).
    - Stronger signals override weaker ones.
    - Thread-safe; can be updated from background threads.
    """

    def __init__(self) -> None:
        self._lock             = threading.Lock()
        self._emotion: str     = _DEFAULT_EMOTION
        self._intensity: float = 0.0
        self._last_update: float = time.monotonic()

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def emotion(self) -> str:
        """Current dominant emotion label."""
        self._apply_decay()
        return self._emotion

    @property
    def intensity(self) -> float:
        """Current emotion intensity (0.0–1.0)."""
        self._apply_decay()
        return round(self._intensity, 2)

    def update_from_user_text(self, text: str) -> str:
        """
        Update emotion state based on user's message.
        Returns the detected emotion label.
        """
        emotion, confidence = classify_emotion(text)
        if confidence > 0.0:
            self._update(emotion, confidence * 0.8)  # user text has 0.8× weight
        return self._emotion

    def update_from_ai_text(self, text: str) -> str:
        """
        Update emotion state based on AI's own reply text.
        Returns the current emotion label.
        """
        emotion = classify_emotion_from_response(text)
        if emotion:
            self._update(emotion, 0.6)  # AI text has 0.6× weight
        return self._emotion

    def update_from_tagged_emotion(self, emotion_tag: str) -> str:
        """
        Directly set emotion from a bracket tag extracted by EmotionStreamParser.
        This has the highest trust/weight as it comes from the model's own signal.
        """
        tag = emotion_tag.lower().strip()
        if tag:
            self._update(tag, 0.9)
        return self._emotion

    def update_from_event(self, event: str) -> str:
        """
        Update emotion based on a named system event.
        Events: 'user_arrived', 'user_left', 'task_success', 'task_failed', 'idle'
        """
        event_emotions: dict[str, tuple[str, float]] = {
            "user_arrived":  ("happy", 0.8),
            "user_left":     ("sad", 0.5),
            "task_success":  ("proud", 0.75),
            "task_failed":   ("sad", 0.5),
            "idle_short":    ("bored", 0.3),
            "idle_long":     ("sad", 0.4),
            "error":         ("confused", 0.5),
        }
        if event in event_emotions:
            emotion, weight = event_emotions[event]
            self._update(emotion, weight)
        return self._emotion

    def get_avatar_hints(self) -> dict[str, str]:
        """Return avatar hints dict for API response (emotion, expression, motion)."""
        return get_avatar_hints(self.emotion)

    def get_expression(self) -> str:
        """Return Live2D expression name for current emotion."""
        return get_expression(self.emotion)

    def get_motion(self) -> str:
        """Return Live2D motion group for current emotion."""
        return get_motion(self.emotion)

    def snapshot(self) -> dict:
        """Return a serializable snapshot of current emotion state."""
        return {
            "emotion":    self.emotion,
            "intensity":  self.intensity,
            "expression": self.get_expression(),
            "motion":     self.get_motion(),
        }

    def reset(self) -> None:
        """Reset to neutral."""
        with self._lock:
            self._emotion   = _DEFAULT_EMOTION
            self._intensity = 0.0
            self._last_update = time.monotonic()

    # ── Internal helpers ───────────────────────────────────────────────────

    def _update(self, new_emotion: str, weight: float) -> None:
        """
        Update internal state.
        New signals override if they have higher weight than current intensity.
        Same emotion type always reinforces.
        """
        self._apply_decay()
        with self._lock:
            if new_emotion == self._emotion:
                # Reinforce existing emotion
                self._intensity = min(1.0, self._intensity + weight * 0.3)
            elif weight > self._intensity * 0.6:
                # Strong enough to override
                self._emotion   = new_emotion
                self._intensity = weight
            self._last_update = time.monotonic()

    def _apply_decay(self) -> None:
        """Decay emotion intensity based on elapsed time."""
        now     = time.monotonic()
        elapsed = now - self._last_update
        if elapsed < 10:   # no decay for first 10 seconds
            return
        decay   = elapsed / _DECAY_INTERVAL
        with self._lock:
            self._intensity = max(0.0, self._intensity - decay)
            if self._intensity <= _MIN_INTENSITY:
                self._emotion   = _DEFAULT_EMOTION
                self._intensity = 0.0
            self._last_update = now


# ── Global singleton ───────────────────────────────────────────────────────────
emotion_engine = EmotionEngine()
