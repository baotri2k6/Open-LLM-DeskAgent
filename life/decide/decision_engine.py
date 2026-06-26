"""Decision Engine — decides whether and what the companion should proactively say."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional

from life.observe.observer import LifeContext


@dataclass
class Decision:
    """Result of the decision engine's evaluation."""

    should_act: bool                     = False
    action_type: str                     = "idle"   # "proactive_message", "reminder", "greeting", "idle"
    message_hint: str                    = ""       # Topic/hint for what to say
    next_check_seconds: float            = 60.0    # When to check again


class DecisionEngine:
    """
    Evaluates LifeContext and decides if the companion should proactively act.

    Decision priority (highest first):
    1. Morning greeting (first contact of the day)
    2. Long idle — check in on user
    3. Goal-based proactive message
    4. Random curiosity/share moment (low frequency)
    """

    def __init__(self) -> None:
        self._last_greeted_date: str     = ""
        self._last_proactive_time: float = 0.0
        self._min_proactive_interval     = 600.0   # seconds (10 min default)

    def configure(self, min_proactive_interval: float) -> None:
        """Allow runtime configuration from companion.config.json."""
        self._min_proactive_interval = min_proactive_interval

    def decide(self, context: LifeContext) -> Decision:
        """Evaluate context and return a Decision."""
        now       = time.time()
        today_str = str(time.strftime("%Y-%m-%d"))
        cooldown  = now - self._last_proactive_time < self._min_proactive_interval

        # ── 1. Morning greeting ────────────────────────────────────────────
        if context.is_morning() and self._last_greeted_date != today_str:
            self._last_greeted_date  = today_str
            self._last_proactive_time = now
            return Decision(
                should_act   = True,
                action_type  = "greeting",
                message_hint = "morning_greeting",
                next_check_seconds = 3600,
            )

        # ── 2. Long idle check-in ──────────────────────────────────────────
        if context.user_idle_seconds > 900 and not cooldown:   # 15 min idle
            self._last_proactive_time = now
            return Decision(
                should_act   = True,
                action_type  = "proactive_message",
                message_hint = "idle_long_checkin",
                next_check_seconds = 600,
            )

        # ── 3. Short idle (5 min) → soft prompt ───────────────────────────
        if context.user_idle_seconds > 300 and not cooldown and context.energy > 0.5:
            self._last_proactive_time = now
            return Decision(
                should_act   = True,
                action_type  = "proactive_message",
                message_hint = "idle_short_nudge",
                next_check_seconds = 300,
            )

        # ── 4. Random curiosity moment (low frequency, ~10% chance per check) ──
        if not cooldown and context.energy > 0.6 and random.random() < 0.08:
            hints = [
                "share_fun_fact",
                "ask_about_project",
                "express_curiosity",
                "friendly_check_in",
            ]
            self._last_proactive_time = now
            return Decision(
                should_act   = True,
                action_type  = "proactive_message",
                message_hint = random.choice(hints),
                next_check_seconds = self._min_proactive_interval,
            )

        # ── Default: no action ─────────────────────────────────────────────
        return Decision(
            should_act         = False,
            action_type        = "idle",
            next_check_seconds = 60,
        )


# ── Global singleton ───────────────────────────────────────────────────────────
decision_engine = DecisionEngine()
