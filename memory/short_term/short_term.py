"""Short-term context summary storage."""

from __future__ import annotations


class ShortTermMemory:
    """Buffer for context snapshots and recent alerts."""

    def __init__(self) -> None:
        self.recent_alerts: list[str] = []

    def add_alert(self, alert: str) -> None:
        self.recent_alerts.append(alert)
        if len(self.recent_alerts) > 10:
            self.recent_alerts = self.recent_alerts[-10:]

    def get_alerts(self) -> list[str]:
        return self.recent_alerts


# Global singleton
short_term_memory = ShortTermMemory()
