"""BeliefStore — kho lưu trữ niềm tin (Beliefs) của companion.

Lưu trữ các phán đoán/niềm tin của companion về thế giới, người dùng, và bản thân.
Mỗi niềm tin đi kèm với độ tin cậy (confidence score 0.0 -> 1.0) cập nhật qua thời gian.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("ai-companion.belief.store")


@dataclass
class Belief:
    """Định nghĩa một niềm tin cụ thể."""
    key:         str
    value:       str
    confidence:  float = 0.5  # 0.0 -> 1.0
    updated_at:  float = field(default_factory=time.time)
    source:      str = "observation"  # observation | direct_feedback | deduction


class BeliefStore:
    """Quản lý các niềm tin của companion."""

    def __init__(self) -> None:
        self._beliefs: Dict[str, Belief] = {}

    def set_belief(self, key: str, value: str, confidence: float = 0.5, source: str = "observation") -> Belief:
        """Đăng ký hoặc cập nhật một niềm tin."""
        belief = Belief(
            key=key,
            value=value,
            confidence=max(0.0, min(1.0, confidence)),
            source=source
        )
        self._beliefs[key] = belief
        logger.info("Belief updated: %s = %s (Confidence=%.2f)", key, value, confidence)
        return belief

    def get_belief(self, key: str) -> Optional[Belief]:
        """Lấy thông tin niềm tin theo key."""
        return self._beliefs.get(key)

    def decay_confidence(self, key: str, amount: float = 0.05) -> None:
        """Giảm độ tin cậy của niềm tin theo thời gian (khi lâu không kiểm chứng)."""
        belief = self.get_belief(key)
        if belief:
            belief.confidence = max(0.0, belief.confidence - amount)
            belief.updated_at = time.time()

    def list_all_beliefs(self) -> List[Belief]:
        """Liệt kê toàn bộ niềm tin."""
        return list(self._beliefs.values())


# Global singleton
belief_store = BeliefStore()
