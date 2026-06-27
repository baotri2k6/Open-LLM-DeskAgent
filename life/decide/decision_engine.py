"""DecisionEngine — tích hợp MotivationManager để quyết định thông minh hơn.

Nâng cấp từ time-based sang motivation-driven decisions.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional

from life.observe.observer import LifeContext

import logging
logger = logging.getLogger("ai-companion.life.decide")


@dataclass
class Decision:
    """Result of the decision engine's evaluation."""

    should_act:         bool  = False
    action_type:        str   = "idle"   # proactive_message | greeting | curiosity | idle
    message_hint:       str   = ""       # Topic/hint hoặc suggested message
    next_check_seconds: float = 60.0


class DecisionEngine:
    """Evaluates LifeContext + MotivationSignal và quyết định companion làm gì.

    Decision priority:
    1. Morning greeting (first contact of the day)
    2. MotivationManager signal (curiosity / boredom / need)
    3. Long idle check-in
    4. Random low-frequency sharing
    """

    def __init__(self) -> None:
        self._last_greeted_date:   str   = ""
        self._last_proactive_time: float = 0.0
        self._min_proactive_interval     = 600.0   # seconds

    def configure(self, min_proactive_interval: float) -> None:
        self._min_proactive_interval = min_proactive_interval

    def decide(self, context: LifeContext) -> Decision:
        """Evaluate context and return a Decision."""
        now       = time.time()
        today_str = time.strftime("%Y-%m-%d")
        cooldown  = (now - self._last_proactive_time) < self._min_proactive_interval

        # ── 1. Morning greeting ────────────────────────────────────────────
        if context.is_morning() and self._last_greeted_date != today_str:
            self._last_greeted_date   = today_str
            self._last_proactive_time = now
            return Decision(
                should_act=True,
                action_type="greeting",
                message_hint="morning_greeting",
                next_check_seconds=3600,
            )

        # ── 2. MotivationManager signal ────────────────────────────────────
        if not cooldown:
            motivation_signal = self._get_motivation_signal()
            if motivation_signal and motivation_signal.get("should_be_proactive"):
                self._last_proactive_time = now
                reason  = motivation_signal.get("proactive_reason", "")
                message = motivation_signal.get("proactive_message", "")
                return Decision(
                    should_act=True,
                    action_type=f"proactive_{reason}" if reason else "proactive_message",
                    message_hint=message or "express_curiosity",
                    next_check_seconds=self._min_proactive_interval,
                )

        # ── 3. Long idle check-in ──────────────────────────────────────────
        if context.user_idle_seconds > 900 and not cooldown:
            self._last_proactive_time = now
            return Decision(
                should_act=True,
                action_type="proactive_message",
                message_hint="idle_long_checkin",
                next_check_seconds=600,
            )

        # ── 4. Short idle + energy ─────────────────────────────────────────
        if context.user_idle_seconds > 300 and not cooldown and context.energy > 0.5:
            self._last_proactive_time = now
            return Decision(
                should_act=True,
                action_type="proactive_message",
                message_hint="idle_short_nudge",
                next_check_seconds=300,
            )

        # ── 5. Low-frequency random sharing ───────────────────────────────
        if not cooldown and context.energy > 0.6 and random.random() < 0.08:
            hints = [
                "share_fun_fact", "ask_about_project",
                "express_curiosity", "friendly_check_in",
            ]
            self._last_proactive_time = now
            return Decision(
                should_act=True,
                action_type="proactive_message",
                message_hint=random.choice(hints),
                next_check_seconds=self._min_proactive_interval,
            )

        # ── Default: no action ─────────────────────────────────────────────
        return Decision(should_act=False, action_type="idle", next_check_seconds=60)

    def _get_motivation_signal(self) -> Optional[dict]:
        """Lấy motivation signal từ MotivationManager nếu available."""
        try:
            from motivation.motivation_manager import motivation_manager
            signal = motivation_manager.tick()
            return {
                "should_be_proactive": signal.should_be_proactive,
                "proactive_reason":    signal.proactive_reason,
                "proactive_message":   signal.proactive_message,
            }
        except Exception as e:
            logger.debug("MotivationManager unavailable: %s", e)
            return None


# Global singleton
decision_engine = DecisionEngine()
