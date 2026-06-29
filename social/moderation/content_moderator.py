"""Moderates content for Twitch/Discord/Telegram streams."""

from __future__ import annotations

import logging
import re
from typing import Dict, List

logger = logging.getLogger("ai-companion.social.moderation")


class ContentModerator:
    """Moderates stream messages for safety, toxicity and spam."""

    def __init__(self) -> None:
        # Prepopulate simple toxicity word patterns
        self._bad_words = [
            r"fck", r"shit", r"toxic", r"chửi", r"bậy", r"ngốc"
        ]
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self._bad_words
        ]

    def add_blacklisted_word(self, word: str) -> None:
        """Add custom pattern to content filter blacklist."""
        self._compiled_patterns.append(re.compile(re.escape(word), re.IGNORECASE))
        logger.info("ContentModerator: Added blacklisted word: '%s'", word)

    def evaluate(self, username: str, message: str) -> dict:
        """Evaluate a message for stream moderation rules.
        
        Returns:
            Dict indicating whether message is flagged and detail reasons.
        """
        message_clean = message.strip()
        
        # 1. Check for bad words
        for pattern in self._compiled_patterns:
            if pattern.search(message_clean):
                logger.warning("ContentModerator: Flagged message from %s (Toxic/Banned language)", username)
                return {
                    "is_flagged": True,
                    "reason": "toxic_language",
                    "action": "warn"
                }

        # 2. Check for spam (excessive caps or length)
        caps_ratio = sum(1 for c in message_clean if c.isupper()) / (len(message_clean) + 1)
        if len(message_clean) > 300 or (len(message_clean) > 20 and caps_ratio > 0.7):
            logger.warning("ContentModerator: Flagged message from %s (Spam/Excessive caps)", username)
            return {
                "is_flagged": True,
                "reason": "spam",
                "action": "delete"
            }

        return {"is_flagged": False, "reason": None, "action": None}


# Global singleton
content_moderator = ContentModerator()
