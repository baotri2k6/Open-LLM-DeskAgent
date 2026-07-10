"""HotkeyManager — quản lý đăng ký phím tắt toàn cục (Global Hotkeys).

Cho phép người dùng gọi nhanh companion bằng phím tắt (ví dụ Alt+Space để bật VAD/STT).
Hỗ trợ fallback nếu thư viện hook phím hệ thống không khả dụng.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict

logger = logging.getLogger("ai-companion.interaction.hotkey")


class HotkeyManager:
    """Quản lý các phím tắt toàn cục của ứng dụng."""

    def __init__(self) -> None:
        self._hotkeys: Dict[str, Callable] = {}
        self._keyboard_module = None
        self._is_listening = False
        
        # Thử nạp thư viện phím tắt hệ thống
        try:
            import keyboard
            self._keyboard_module = keyboard
            logger.info("HotkeyManager: using system 'keyboard' module")
        except ImportError:
            try:
                from pynput import keyboard
                self._keyboard_module = keyboard
                logger.info("HotkeyManager: using system 'pynput' module")
            except ImportError:
                logger.warning("HotkeyManager: No global keyboard hook library installed (fallback active)")

    def register(self, hotkey_str: str, callback: Callable) -> bool:
        """Đăng ký phím tắt mới.

        Args:
            hotkey_str: Tổ hợp phím (ví dụ "alt+space").
            callback: Hàm sẽ gọi khi phím được nhấn.
        """
        self._hotkeys[hotkey_str] = callback
        logger.info("Hotkey registered: %s", hotkey_str)

        if not self._keyboard_module:
            return False

        try:
            # Register using keyboard module
            if hasattr(self._keyboard_module, "add_hotkey"):
                self._keyboard_module.add_hotkey(hotkey_str, callback)
                return True
            # Register using pynput
            else:
                # pynput listener will be handled in start_listening
                return True
        except Exception as e:
            logger.error("Failed to register system hotkey '%s': %s", hotkey_str, e)
            return False

    def start_listening(self) -> None:
        """Bắt đầu lắng nghe phím tắt toàn hệ thống (nếu thư viện được hỗ trợ)."""
        if self._is_listening:
            return
        
        self._is_listening = True

        if not self._keyboard_module:
            return

        try:
            # Nếu dùng pynput, khởi chạy listener
            if not hasattr(self._keyboard_module, "add_hotkey"):
                # pynput.keyboard mapping
                hotkey_map = {}
                for hk, cb in self._hotkeys.items():
                    # Map standard string keys to pynput format if needed
                    # basic mapping format: <alt>+<space>
                    pynput_hk = hk.replace("alt", "<alt>").replace("ctrl", "<ctrl>").replace("shift", "<shift>")
                    hotkey_map[pynput_hk] = cb
                
                # Dynamic start listener thread
                listener = self._keyboard_module.GlobalHotKeys(hotkey_map)
                listener.start()
                logger.info("HotkeyManager (pynput): Listener thread started")
        except Exception as e:
            logger.error("Failed to start hotkey listener: %s", e)

    def stop_listening(self) -> None:
        """Dừng lắng nghe phím tắt."""
        self._is_listening = False


# Global singleton
hotkey_manager = HotkeyManager()
