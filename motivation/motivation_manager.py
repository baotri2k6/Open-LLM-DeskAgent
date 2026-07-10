"""MotivationManager — orchestrates toàn bộ hệ thống motivation.

Tổng hợp signals từ Needs, Drives, Boredom, Curiosity
thành một "drive vector" duy nhất để Life Loop sử dụng.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from motivation.needs import CompanionNeeds, companion_needs
from motivation.boredom import BoredomDetector, boredom_detector
from motivation.curiosity import CuriositySystem, curiosity_system
from motivation.drives import IntrinsicDrives, intrinsic_drives

logger = logging.getLogger("ai-companion.motivation.manager")


@dataclass
class MotivationSignal:
    """Tín hiệu motivation tổng hợp để Life Loop xử lý."""
    should_be_proactive:   bool    # Có nên chủ động lên tiếng không?
    proactive_reason:      str     # Lý do (boredom / curiosity / need)
    proactive_message:     str     # Gợi ý nội dung (có thể empty)
    boredom_level:         float   # 0.0 → 1.0
    wellbeing:             float   # Tổng thể wellbeing 0.0 → 1.0
    dominant_drive:        str     # Drive mạnh nhất hiện tại
    personality_vector:    dict    # Cho system prompt


class MotivationManager:
    """Orchestrates hệ thống motivation.

    Được gọi bởi LifeLoop mỗi cycle để quyết định companion
    có nên làm gì chủ động không.
    """

    def __init__(
        self,
        needs:     CompanionNeeds  = companion_needs,
        boredom:   BoredomDetector = boredom_detector,
        curiosity: CuriositySystem = curiosity_system,
        drives:    IntrinsicDrives = intrinsic_drives,
    ) -> None:
        self._needs     = needs
        self._boredom   = boredom
        self._curiosity = curiosity
        self._drives    = drives

    def tick(self) -> MotivationSignal:
        """Tính toán motivation signal hiện tại.

        Gọi mỗi life cycle (mỗi 30 giây).
        Returns:
            MotivationSignal để Life Loop quyết định action.
        """
        # Update needs decay
        self._needs.tick()

        # Get boredom state
        boredom_state = self._boredom.tick()

        # Determine proactive action
        proactive = False
        reason = ""
        message = ""

        # Priority 1: Curiosity question (nếu có topic thú vị)
        curious_question = self._curiosity.get_curious_question()
        if curious_question:
            proactive = True
            reason = "curiosity"
            message = curious_question

        # Priority 2: Boredom (nếu idle quá lâu)
        elif self._boredom.should_trigger():
            proactive = True
            reason = "boredom"
            self._boredom.mark_triggered()

            # Chọn action dựa trên idle time
            idle_min = boredom_state.idle_minutes
            if idle_min < 10:
                message = ""  # Để LLM tự sinh nội dung
            elif idle_min < 30:
                message = "Mày đang làm gì vậy?"
            else:
                message = ""  # Đã idle lâu, cần trigger tự nhiên hơn

        # Priority 3: Urgent need
        urgent_need = self._needs.get_most_urgent()
        if urgent_need and not proactive:
            proactive = True
            reason = f"need:{urgent_need.name}"
            self._needs.satisfy(urgent_need.name, 0.2)

        # Get dominant drive
        active_drives = self._drives.get_active_drives()
        dominant_drive = active_drives[0].name if active_drives else "helpfulness"

        return MotivationSignal(
            should_be_proactive=proactive,
            proactive_reason=reason,
            proactive_message=message,
            boredom_level=boredom_state.level,
            wellbeing=self._needs.overall_wellbeing(),
            dominant_drive=dominant_drive,
            personality_vector=self._drives.get_personality_vector(),
        )

    def on_conversation(self, user_text: str = "") -> None:
        """Gọi khi có cuộc trò chuyện — update tất cả modules."""
        self._needs.on_conversation()
        self._boredom.on_activity()

        # Extract topics từ conversation cho curiosity
        if user_text:
            topics = self._curiosity.extract_topics_from_text(user_text)
            for topic in topics:
                self._curiosity.add_topic(topic, interest=0.5, source="conversation")

        logger.debug("Motivation updated after conversation")

    def on_task_completed(self) -> None:
        """Gọi khi companion hoàn thành task."""
        self._needs.on_task_completed()
        self._boredom.on_activity()

    def on_learned_something(self, topic: str = "") -> None:
        """Gọi khi companion học được điều mới."""
        self._needs.on_learned_something()
        if topic:
            self._curiosity.add_topic(topic, interest=0.7, source="learning")

    def describe_for_prompt(self) -> str:
        """Mô tả motivation state cho system prompt."""
        wellbeing = self._needs.overall_wellbeing()
        boredom = self._boredom.get_intensity_label()
        drives_desc = self._drives.describe_for_prompt()

        lines = [
            f"Wellbeing: {wellbeing:.0%}",
            f"Boredom: {boredom}",
        ]
        if drives_desc:
            lines.append(drives_desc)

        return "\n".join(lines)

    def get_state_snapshot(self) -> dict:
        """Snapshot đầy đủ cho API /companion/state."""
        return {
            "needs": self._needs.get_summary(),
            "boredom": {
                "level": self._boredom.tick().level,
                "label": self._boredom.get_intensity_label(),
            },
            "curiosity": {
                "top_interests": self._curiosity.get_top_interests(3),
            },
            "drives": self._drives.get_personality_vector(),
            "wellbeing": self._needs.overall_wellbeing(),
        }


# Global singleton
motivation_manager = MotivationManager()
