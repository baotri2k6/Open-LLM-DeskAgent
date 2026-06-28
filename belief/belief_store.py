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


try:
    from config.config import WRITABLE_ROOT
    _BELIEFS_PATH = WRITABLE_ROOT / "data" / "user_beliefs.json"
except Exception:
    from pathlib import Path
    _BELIEFS_PATH = Path("data") / "user_beliefs.json"


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

    def __init__(self, beliefs_path: Optional[Path] = None) -> None:
        self._path = beliefs_path or _BELIEFS_PATH
        self._beliefs: Dict[str, Belief] = {}
        self._load()

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
        self._save()
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
            self._save()

    def list_all_beliefs(self) -> List[Belief]:
        """Liệt kê toàn bộ niềm tin."""
        return list(self._beliefs.values())

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for key, belief in self._beliefs.items():
                data[key] = {
                    "key": belief.key,
                    "value": belief.value,
                    "confidence": belief.confidence,
                    "updated_at": belief.updated_at,
                    "source": belief.source
                }
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save beliefs: %s", e)

    def _load(self) -> None:
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, val in data.items():
                    self._beliefs[key] = Belief(
                        key=val["key"],
                        value=val["value"],
                        confidence=val["confidence"],
                        updated_at=val["updated_at"],
                        source=val["source"]
                    )
        except Exception as e:
            logger.error("Failed to load beliefs: %s", e)


# Global singleton
belief_store = BeliefStore()

