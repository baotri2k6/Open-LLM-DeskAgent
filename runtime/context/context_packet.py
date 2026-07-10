"""Context packet — unified snapshot passed between modules."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ContextPacket:
    """Unified context snapshot passed between perception, cognition, and agent systems."""

    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    user_message: str = ""
    ocr_text: str = ""
    activity: str = "unknown"
    idle_seconds: float = 0.0
    active_window: str = "unknown"
    hour_of_day: int = field(default_factory=lambda: datetime.now().hour)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context packet to dict representation for backwards compatibility."""
        return {
            "timestamp": self.timestamp,
            "user_message": self.user_message,
            "screen_text": self.ocr_text,  # maps to screen_text for compatibility
            "idle_time_seconds": self.idle_seconds,  # maps to idle_time_seconds for compatibility
            "activity": self.activity,
            "active_window": self.active_window,
            "hour_of_day": self.hour_of_day,
            **self.metadata
        }

    # Implement dictionary-like get method for backwards compatibility with dict lookups
    def get(self, key: str, default: Any = None) -> Any:
        """Provide dictionary-like get lookup for compatibility."""
        d = self.to_dict()
        return d.get(key, default)

    # Implement key indexing for dictionary-like access
    def __getitem__(self, key: str) -> Any:
        d = self.to_dict()
        return d[key]

    def __contains__(self, key: str) -> bool:
        d = self.to_dict()
        return key in d
