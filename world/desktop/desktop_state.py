"""Captures a lightweight desktop state snapshot."""

from __future__ import annotations

from tools.screen_reader import capture_screenshot
from world.windows.window_tracker import window_tracker


class DesktopState:
    """Tracks active window and screen size without expensive UI automation."""

    def snapshot(self) -> dict:
        screen = capture_screenshot()
        return {
            "active_window": window_tracker.get_active_window(),
            "screen_size": screen.get("size") if screen.get("success") else None,
            "screen_available": bool(screen.get("success")),
        }

    def describe(self) -> str:
        state = self.snapshot()
        win = state["active_window"]
        return f"Desktop active window: {win.get('title', 'unknown')} ({win.get('app', 'unknown')})"


desktop_state = DesktopState()
