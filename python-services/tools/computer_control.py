"""Computer control tools — mouse, keyboard, and shell execution."""

from __future__ import annotations

import os
import sys
import subprocess
import pyautogui

# Tắt chế độ fail-safe của pyautogui để tránh crash khi rê chuột sát góc màn hình
pyautogui.FAILSAFE = False


def mouse_click(x: int, y: int, button: str = "left", double_click: bool = False) -> dict:
    """Click chuột tại tọa độ x, y."""
    try:
        if double_click:
            pyautogui.doubleClick(x, y, button=button)
        else:
            pyautogui.click(x, y, button=button)
        return {"success": True, "message": f"Clicked {button} at ({x}, {y})"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def mouse_move(x: int, y: int) -> dict:
    """Di chuyển chuột đến tọa độ x, y."""
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        return {"success": True, "message": f"Moved mouse to ({x}, {y})"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def keyboard_type(text: str) -> dict:
    """Gõ chuỗi văn bản."""
    try:
        pyautogui.write(text, interval=0.01)
        return {"success": True, "message": f"Typed text: {text[:30]}..."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def keyboard_press(keys: str) -> dict:
    """Ấn một phím hoặc tổ hợp phím (ví dụ: 'ctrl+c', 'enter')."""
    try:
        # Hỗ trợ tổ hợp phím cách nhau bởi dấu cộng
        parts = [p.strip() for p in keys.split("+")]
        if len(parts) > 1:
            pyautogui.hotkey(*parts)
        else:
            pyautogui.press(keys)
        return {"success": True, "message": f"Pressed keys: {keys}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def execute_command(command: str) -> dict:
    """Chạy lệnh shell (cmd/powershell trên Windows, bash/sh trên Unix)."""
    try:
        # Sử dụng shell tương ứng của hệ điều hành
        use_shell = sys.platform == "win32"
        
        proc = subprocess.run(
            command,
            shell=use_shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
        
        def decode_output(b: bytes) -> str:
            for enc in ("utf-8", "utf-16", "cp1252", "cp437", "ansi"):
                try:
                    return b.decode(enc)
                except UnicodeDecodeError:
                    continue
            return b.decode("utf-8", errors="replace")

        stdout = decode_output(proc.stdout)
        stderr = decode_output(proc.stderr)
        
        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command execution timed out (60s)."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
