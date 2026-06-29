"""Extracts lessons from each life cycle iteration, learning habits, traits and preferences dynamically."""

from __future__ import annotations

import logging
from typing import Any
from belief.user_model import user_model
from belief.belief_updater import belief_updater

logger = logging.getLogger("ai-companion.life.learn")


class LifeLearner:
    """Extracts lessons from each life cycle iteration, learning habits, traits and preferences dynamically."""

    def __init__(self) -> None:
        self._activity_counters: dict[str, int] = {}
        self._night_active_count = 0
        self._morning_active_count = 0
        self._dev_focus_count = 0
        self._gaming_focus_count = 0
        self._proactive_rejections = 0
        self._proactive_accepts = 0

    def learn_cycle_lessons(self, context: Any, decision: Any, success: bool) -> None:
        """Learn user habits or task preferences based on cycle outcomes."""
        if not success:
            return

        # --- 1. Learn from user activity ---
        activity = getattr(context, "activity", None)
        if not activity:
            activity = getattr(context, "last_user_activity", None)
        if not activity and isinstance(context, dict):
            activity = context.get("activity") or context.get("last_user_activity")

        if activity and activity != "unknown":
            self._activity_counters[activity] = self._activity_counters.get(activity, 0) + 1
            count = self._activity_counters[activity]

            # If we observe this activity at least 3 times, promote to a strong preference/habit
            if count >= 3:
                user_model.set_preference("favorite_activity", activity)
                belief_updater.register_evidence(f"user.habit.{activity}", "active", confidence=0.8, source="observation")
                logger.info("LifeLearner: Promoted '%s' to favorite activity (observed %d times)", activity, count)

            # Trait inference from activity
            if activity == "coding":
                self._dev_focus_count += 1
                if self._dev_focus_count >= 3:
                    belief_updater.register_evidence("user.trait.developer", "true", confidence=0.85, source="observation")
            elif activity == "gaming":
                self._gaming_focus_count += 1
                if self._gaming_focus_count >= 3:
                    belief_updater.register_evidence("user.trait.gamer", "true", confidence=0.8, source="observation")

        # --- 2. Temporal pattern analysis (Work Hours preference) ---
        hour = getattr(context, "hour_of_day", None)
        if hour is None and isinstance(context, dict):
            hour = context.get("hour_of_day")
        if hour is not None:
            if hour >= 22 or hour <= 4:
                self._night_active_count += 1
                if self._night_active_count >= 3:
                    belief_updater.register_evidence("user.trait.night_owl", "true", confidence=0.9, source="observation")
                    logger.info("LifeLearner: Inferred user trait 'night_owl' = 'true' (observed %d late-night activities)", self._night_active_count)
            elif 5 <= hour <= 9:
                self._morning_active_count += 1
                if self._morning_active_count >= 3:
                    belief_updater.register_evidence("user.trait.early_bird", "true", confidence=0.85, source="observation")
                    logger.info("LifeLearner: Inferred user trait 'early_bird' = 'true' (observed %d morning activities)", self._morning_active_count)

        # --- 3. App/Window-based preference learning ---
        active_window = getattr(context, "active_window", None)
        if not active_window and isinstance(context, dict):
            active_window = context.get("active_window")
        if active_window and active_window != "unknown":
            window_lower = active_window.lower()
            
            # Learn specific editor preferences
            detected_editor = None
            if "visual studio code" in window_lower or "vscode" in window_lower or "vs code" in window_lower:
                detected_editor = "vscode"
            elif "pycharm" in window_lower:
                detected_editor = "pycharm"
            elif "sublime" in window_lower:
                detected_editor = "sublime_text"
            elif "cursor" in window_lower:
                detected_editor = "cursor"

            if detected_editor:
                user_model.set_preference("editor", detected_editor)
                belief_updater.register_evidence("user.preference.editor", detected_editor, confidence=0.95, source="observation")
                
                # Wire to knowledge graph
                try:
                    from knowledge.graph.knowledge_graph import knowledge_graph
                    knowledge_graph.add_relation("User", detected_editor, "PREFERS_EDITOR")
                except Exception:
                    pass

        # --- 4. Disturbance / Proactivity Feedback loops ---
        if decision and getattr(decision, "should_act", False):
            # Check response outcome: did the user ignore or reject?
            user_msg = getattr(context, "user_message", None)
            if not user_msg and isinstance(context, dict):
                user_msg = context.get("user_message")

            idle_time = getattr(context, "idle_seconds", 0.0)
            if idle_time is None and isinstance(context, dict):
                idle_time = context.get("idle_time_seconds") or 0.0

            if not user_msg and idle_time > 300:
                self._proactive_rejections += 1
                if self._proactive_rejections >= 3:
                    belief_updater.register_evidence("companion.etiquette.disturbance_level", "low", confidence=0.8, source="interaction_feedback")
                    logger.info("LifeLearner: User is ignoring proactive triggers. Lowering companion disturbance level.")
            elif user_msg:
                self._proactive_accepts += 1
                if self._proactive_accepts >= 3:
                    belief_updater.register_evidence("companion.etiquette.disturbance_level", "normal", confidence=0.8, source="interaction_feedback")

        # --- 5. Learn from user text in context packet if available ---
        user_msg = getattr(context, "user_message", None)
        if not user_msg and isinstance(context, dict):
            user_msg = context.get("user_message")

        if user_msg:
            # Dynamically learn preferences mentioned by the user
            from learning.knowledge.knowledge_extractor import knowledge_extractor
            extracted = knowledge_extractor.extract_from_text(user_msg)
            for k, v in extracted.items():
                logger.info("LifeLearner: Learnt fact from user message: %s = %s", k, v)


# Global singleton
life_learner = LifeLearner()
