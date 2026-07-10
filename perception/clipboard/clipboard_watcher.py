"""Monitors OS clipboard for content changes."""

from __future__ import annotations

import time


class ClipboardWatcher:
    """Polling clipboard watcher with graceful fallback."""

    def __init__(self) -> None:
        self._last_text = ""
        self._last_change = 0.0

    def read_text(self) -> str:
        try:
            import pyperclip
            value = pyperclip.paste()
            return value if isinstance(value, str) else ""
        except Exception:
            return self._last_text

    def poll(self) -> dict:
        current = self.read_text()
        changed = current != self._last_text
        if changed:
            self._last_text = current
            self._last_change = time.time()
        return {
            "changed": changed,
            "text": current,
            "last_change": self._last_change,
            "kind": "url" if current.startswith(("http://", "https://")) else "text",
        }

    def get_current_context(self) -> str:
        return self._last_text or self.read_text()


clipboard_watcher = ClipboardWatcher()
