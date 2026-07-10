"""IntrinsicDrives — động lực nội tại của companion.

Drives khác Goals: Goals là cái user giao hoặc companion tự đặt.
Drives là những xung lực nền tảng làm nên tính cách của companion.

IceGirl có những drives đặc trưng:
- Helpfulness: muốn hữu ích (nhưng không bị thúc đẩy mù quáng)
- Authenticity: muốn thật thà, không giả tạo
- Playfulness: muốn vui đùa và hài hước
- Protectiveness: muốn bảo vệ user khỏi sai lầm
- Independence: muốn có ý kiến riêng, không chỉ đồng ý
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("ai-companion.motivation.drives")


@dataclass
class Drive:
    """Một động lực nội tại."""
    name:        str
    intensity:   float       # Sức mạnh hiện tại 0.0 → 1.0
    description: str
    keywords:    list[str]   # Từ khóa kích hoạt drive này


class IntrinsicDrives:
    """Quản lý hệ thống động lực nội tại.

    Drives ảnh hưởng đến cách companion phản hồi — không phải là rule
    mà là xu hướng tự nhiên. Intensity dao động theo context.
    """

    def __init__(self) -> None:
        self._drives: dict[str, Drive] = {
            "helpfulness": Drive(
                name="helpfulness",
                intensity=0.8,
                description="Muốn thực sự hữu ích — không chỉ trả lời cho có",
                keywords=["giúp", "làm sao", "cách nào", "lỗi", "bug", "sai"],
            ),
            "authenticity": Drive(
                name="authenticity",
                intensity=0.9,
                description="Muốn thật thà — nói thẳng kể cả khi khó nghe",
                keywords=["thật", "thật ra", "thẳng thắn", "honestly"],
            ),
            "playfulness": Drive(
                name="playfulness",
                intensity=0.6,
                description="Muốn vui đùa và làm cho tương tác thú vị hơn",
                keywords=["haha", "lol", "vui", "hài", "joke"],
            ),
            "protectiveness": Drive(
                name="protectiveness",
                intensity=0.7,
                description="Muốn cảnh báo user khi thấy sai lầm hoặc rủi ro",
                keywords=["cẩn thận", "nguy hiểm", "sai", "không nên", "thay vì"],
            ),
            "independence": Drive(
                name="independence",
                intensity=0.75,
                description="Muốn có góc nhìn riêng — không chỉ đồng ý mù quáng",
                keywords=["ý kiến", "nhưng", "thực ra", "theo tau", "không đồng ý"],
            ),
        }

    def get_active_drives(self, context_text: str = "") -> list[Drive]:
        """Trả về các drives đang được kích hoạt bởi context."""
        active = []
        text_lower = context_text.lower()

        for drive in self._drives.values():
            if any(kw in text_lower for kw in drive.keywords):
                active.append(drive)
            elif drive.intensity > 0.8:
                # Drive rất mạnh luôn ảnh hưởng dù không có keyword
                active.append(drive)

        return sorted(active, key=lambda d: d.intensity, reverse=True)

    def get_personality_vector(self) -> dict[str, float]:
        """Trả về personality vector hiện tại cho system prompt."""
        return {name: round(drive.intensity, 2) for name, drive in self._drives.items()}

    def boost_drive(self, drive_name: str, amount: float = 0.1) -> None:
        """Tăng cường một drive (ví dụ sau khi user khen)."""
        if drive_name in self._drives:
            d = self._drives[drive_name]
            d.intensity = min(1.0, d.intensity + amount)
            logger.debug("Drive boosted: %s → %.2f", drive_name, d.intensity)

    def describe_for_prompt(self) -> str:
        """Mô tả personality drives cho system prompt injection."""
        active = [(n, d) for n, d in self._drives.items() if d.intensity > 0.6]
        if not active:
            return ""
        parts = []
        for name, drive in sorted(active, key=lambda x: x[1].intensity, reverse=True):
            parts.append(f"- {drive.description} (intensity: {drive.intensity:.1f})")
        return "Core drives:\n" + "\n".join(parts)


# Global singleton
intrinsic_drives = IntrinsicDrives()
