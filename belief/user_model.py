"""UserModel — mô hình hóa hồ sơ hành vi và sở thích của người dùng.

Trích xuất thông tin hồ sơ người dùng từ các niềm tin (Beliefs) đã lưu trữ.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from belief.belief_store import belief_store

logger = logging.getLogger("ai-companion.belief.user_model")


class UserModel:
    """Mô hình hóa thông tin người dùng."""

    def __init__(self) -> None:
        pass

    def get_preference(self, key: str, default: str = "") -> str:
        """Lấy sở thích của user dựa trên belief."""
        belief_key = f"user.preference.{key}"
        belief = belief_store.get_belief(belief_key)
        if belief and belief.confidence > 0.4:
            return belief.value
        return default

    def set_preference(self, key: str, value: str, confidence: float = 0.8) -> None:
        """Thiết lập sở thích của user."""
        belief_key = f"user.preference.{key}"
        belief_store.set_belief(belief_key, value, confidence, source="direct_feedback")

    def get_user_traits(self) -> List[str]:
        """Lấy danh sách các đặc điểm tính cách của user dựa trên quan sát.

        Ví dụ: ['night_owl', 'patient', 'likes_fast_responses']
        """
        traits = []
        for belief in belief_store.list_all_beliefs():
            if belief.key.startswith("user.trait.") and belief.confidence > 0.6:
                if belief.value.lower() == "true":
                    traits.append(belief.key.replace("user.trait.", ""))
        return traits

    def set_user_trait(self, trait_name: str, active: bool = True, confidence: float = 0.5) -> None:
        """Thiết lập đặc điểm tính cách của user."""
        belief_key = f"user.trait.{trait_name}"
        belief_store.set_belief(belief_key, str(active), confidence, source="observation")


# Global singleton
user_model = UserModel()
