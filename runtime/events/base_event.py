"""BaseEvent — cấu trúc chuẩn cho mọi event trong hệ thống.

Mọi event đều phải kế thừa hoặc sử dụng class này.
correlation_id cho phép trace toàn bộ một request pipeline qua log.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass
class BaseEvent:
    """Cấu trúc chuẩn cho mọi event trong hệ thống.

    Attributes:
        id: UUID duy nhất của event này.
        timestamp: Thời điểm phát event (UTC).
        source: Module phát event, ví dụ "speech/stt", "cognition".
        correlation_id: ID chung cho toàn bộ một request pipeline.
                        Tất cả events trong cùng một conversation turn
                        chia sẻ correlation_id giống nhau.
        event_type: Tên loại event, khớp với EventType constants.
        version: Schema version — dùng cho migration.
        payload: Dữ liệu tuỳ ý của event.
    """

    event_type:     str      = ""
    source:         str      = ""
    payload:        dict     = field(default_factory=dict)
    id:             UUID     = field(default_factory=uuid4)
    timestamp:      datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: UUID     = field(default_factory=uuid4)
    version:        str      = "1.0"

    # ── Convenience constructors ───────────────────────────────────────────

    @classmethod
    def create(
        cls,
        event_type: str,
        source: str,
        payload: dict | None = None,
        correlation_id: UUID | None = None,
    ) -> "BaseEvent":
        """Tạo event mới với correlation_id tùy chọn."""
        return cls(
            event_type=event_type,
            source=source,
            payload=payload or {},
            correlation_id=correlation_id or uuid4(),
        )

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Chuyển event thành dict có thể JSON-serialize."""
        d = asdict(self)
        d["id"] = str(self.id)
        d["correlation_id"] = str(self.correlation_id)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    def to_json(self) -> str:
        """Chuyển event thành JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "BaseEvent":
        """Tạo BaseEvent từ dict (ví dụ từ WebSocket message)."""
        return cls(
            event_type=data.get("event_type", ""),
            source=data.get("source", ""),
            payload=data.get("payload", {}),
            id=UUID(data["id"]) if "id" in data else uuid4(),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            correlation_id=UUID(data["correlation_id"]) if "correlation_id" in data else uuid4(),
            version=data.get("version", "1.0"),
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    def with_correlation(self, correlation_id: UUID) -> "BaseEvent":
        """Trả về bản copy với correlation_id đã set."""
        from dataclasses import replace
        return replace(self, correlation_id=correlation_id)

    def __str__(self) -> str:
        return f"[{self.event_type}] src={self.source} corr={str(self.correlation_id)[:8]}"
