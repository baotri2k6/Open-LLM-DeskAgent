"""Platform-specific social rules and conversation etiquette."""

from __future__ import annotations


class SocialRules:
    """Small rule engine that decides how intrusive a response may be."""

    QUIET_ACTIVITIES = {"coding", "terminal_work", "meeting", "presentation", "gaming"}

    def should_interrupt(self, activity: str = "unknown", urgency: str = "normal") -> bool:
        if urgency in {"critical", "safety"}:
            return True
        if activity in self.QUIET_ACTIVITIES:
            return False
        return urgency in {"normal", "high"}

    def response_style(self, platform: str = "desktop", relationship_level: str = "Bạn") -> dict:
        platform = platform.lower()
        return {
            "max_length": 180 if platform in {"telegram", "notification"} else 500,
            "allow_teasing": relationship_level in {"Bạn thân", "Tri kỷ"},
            "avoid_spam": True,
            "ask_before_action": True,
        }

    def describe_for_prompt(self, activity: str = "unknown") -> str:
        if activity in self.QUIET_ACTIVITIES:
            return "User may be focused; keep proactive messages quiet and rare."
        return "User is available enough for concise, friendly interaction."


social_rules = SocialRules()
