"""NotificationManager — gửi thông báo hệ thống và thông báo trong app (in-app notifications).

Được gọi khi companion hoàn thành task chạy nền, có nhắc nhở,
hoặc khi companion muốn gửi tin nhắn tự động từ MotivationEngine.
"""

from __future__ import annotations

import logging
from typing import Optional

from runtime.events.event_types import EventType
from runtime.events.base_event import BaseEvent

logger = logging.getLogger("ai-companion.interaction.notifications")


class NotificationManager:
    """Quản lý việc gửi thông báo đến người dùng.

    Tự động chọn kênh phù hợp:
    1. Gửi qua WebSocket sự kiện để Renderer (Electron) hiển thị Toast.
    2. Gửi thông báo hệ thống toàn cục (OS System Notification).
    """

    def __init__(self) -> None:
        self._notify_module = None
        
        # Thử nạp plyer cho OS notifications
        try:
            from plyer import notification
            self._notify_module = notification
            logger.info("NotificationManager: plyer OS notification active")
        except ImportError:
            logger.debug("NotificationManager: plyer not installed (falling back to UI overlay only)")

    def send(
        self,
        title: str,
        message: str,
        notification_type: str = "info",  # info | warning | success | error
        is_system: bool = False
    ) -> None:
        """Gửi thông báo đến user.

        Args:
            title: Tiêu đề thông báo.
            message: Nội dung thông báo.
            notification_type: Phân loại ("info", "warning", "success", "error").
            is_system: Nếu True, thử gửi thông báo cấp OS kể cả khi app đang minimized.
        """
        logger.info("Notification [%s]: %s - %s", notification_type, title, message)

        # ── 1. Gửi Event qua EventBus để UI (Electron) hiển thị ──────────
        try:
            from runtime.eventbus.event_bus import event_bus
            payload = {
                "title": title,
                "message": message,
                "notification_type": notification_type
            }
            # Gửi OBS broadcast hoặc general SYSTEM_READY event style
            event = BaseEvent.create(
                event_type=EventType.OBS_BROADCAST,
                source="notification_manager",
                payload={"sub_type": "toast", "data": payload}
            )
            event_bus.publish(event)
        except Exception as e:
            logger.error("Failed to publish notification event to EventBus: %s", e)

        # ── 2. Gửi OS system notification nếu cần và khả dụng ───────────
        if is_system and self._notify_module:
            try:
                self._notify_module.notify(
                    title=title,
                    message=message,
                    app_name="DeskAgent Companion",
                    timeout=5
                )
            except Exception as e:
                logger.error("Failed to send OS notification: %s", e)


# Global singleton
notification_manager = NotificationManager()
