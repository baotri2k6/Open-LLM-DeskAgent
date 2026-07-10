"""Desktop agent for safe, simple Windows desktop actions."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class DesktopAgent:
    APP_ALIASES = {
        "chrome": ["chrome", "google chrome"],
        "google chrome": ["chrome", "google chrome"],
        "edge": ["msedge", "edge"],
        "coccoc": ["coccoc", "cốc cốc"],
        "cốc cốc": ["coccoc", "cốc cốc"],
        "trình duyệt": ["chrome", "msedge", "coccoc"],
        "browser": ["chrome", "msedge", "coccoc"],
        "trình duyệt web": ["chrome", "msedge", "coccoc"],
        "web browser": ["chrome", "msedge", "coccoc"],
        "web": ["chrome", "msedge", "coccoc"],
        "youtube": ["https://youtube.com"],
        "google": ["https://google.com"],
        "facebook": ["https://facebook.com"],
        "messenger": ["https://messenger.com"],
        "vscode": ["code", "Visual Studio Code"],
        "vs code": ["code", "Visual Studio Code"],
        "visual studio code": ["code", "Visual Studio Code"],
        "notepad": ["notepad"],
        "ghi chu": ["notepad"],
        "máy tính": ["calc"],
        "calculator": ["calc"],
        "explorer": ["explorer"],
        "file explorer": ["explorer"],
        "cmd": ["cmd"],
        "powershell": ["powershell"],
    }

    def _find_coccoc_path(self) -> str | None:
        local_app_data = os.getenv("LOCALAPPDATA", "")
        paths = [
            os.path.join(local_app_data, "CocCoc", "Browser", "Application", "browser.exe") if local_app_data else None,
            "C:\\Program Files\\CocCoc\\Browser\\Application\\browser.exe",
            "C:\\Program Files (x86)\\CocCoc\\Browser\\Application\\browser.exe",
        ]
        for p in paths:
            if p and os.path.exists(p):
                return p
        return None

    async def open_application(self, app_name: str) -> dict:
        app_name = app_name.strip().strip(".")
        name_lower = app_name.lower()

        # Kiểm tra câu lệnh phức hợp hoặc nhiều hành động gộp
        if any(w in name_lower for w in [" và ", " rồi ", " sau đó ", " sau đấy ", " để "]) or len(app_name.split()) > 2:
            return {
                "success": False,
                "error": (
                    f"Yêu cầu mở '{app_name}' có vẻ là một câu lệnh phức hợp hoặc chứa nhiều hành động. "
                    "Vui lòng tách các hành động ra thành các bước gọi công cụ riêng lẻ. "
                    "Ví dụ: trước tiên hãy gọi open_url với địa chỉ trang web cụ thể (như 'https://youtube.com') "
                    "hoặc open_application('chrome') để mở trình duyệt, sau đó ở lượt tiếp theo sử dụng click_element_by_vision "
                    "hoặc keyboard_type để tìm kiếm và bật nhạc."
                ),
                "tried": []
            }
        
        # Kiểm tra xem app_name có trong APP_ALIASES không
        if name_lower in self.APP_ALIASES:
            candidates = self.APP_ALIASES[name_lower]
        else:
            # Nếu không phải là alias, kiểm tra xem nó có phải đường dẫn file tồn tại không
            try:
                p = Path(app_name)
                if p.exists():
                    candidates = [str(p)]
                else:
                    # Chỉ chấp nhận từ đơn thuần chữ cái/số không chứa khoảng trắng (ví dụ: calc, mspaint)
                    if " " not in app_name and len(app_name) < 30 and (app_name.isalnum() or app_name.replace("_", "").replace("-", "").isalnum()):
                        candidates = [app_name]
                    else:
                        candidates = []
            except Exception:
                candidates = []

        if not candidates:
            return {
                "success": False,
                "error": f"Mình chưa tìm thấy ứng dụng '{app_name}'.",
                "tried": []
            }

        for candidate in candidates:
            result = self._try_open(candidate)
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Mình đã mở {app_name}.",
                    "app": app_name,
                }

        return {
            "success": False,
            "error": f"Mình chưa tìm thấy ứng dụng '{app_name}'.",
            "tried": candidates,
        }

    def _try_open(self, command: str) -> dict:
        try:
            if sys.platform == "win32":
                if command in ("coccoc", "cốc cốc"):
                    coccoc_path = self._find_coccoc_path()
                    if coccoc_path:
                        command = coccoc_path

                if Path(command).exists():
                    subprocess.Popen([command], close_fds=True)
                else:
                    subprocess.Popen(["cmd", "/c", "start", "", command], shell=False)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-a", command])
            else:
                subprocess.Popen([command])
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def find_file(self, filename: str) -> dict:
        filename = filename.lower().strip()
        roots = [
            Path.home() / "Desktop",
            Path.home() / "Documents",
            Path.home() / "Downloads",
        ]
        results = []
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if len(results) >= 20:
                    break
                if filename in path.name.lower():
                    results.append(str(path))
        return {"success": bool(results), "results": results}

    async def read_clipboard(self) -> dict:
        try:
            import tkinter

            root = tkinter.Tk()
            root.withdraw()
            text = root.clipboard_get()
            root.destroy()
            return {"success": True, "text": text}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def system_info(self) -> dict:
        return {
            "success": True,
            "platform": sys.platform,
            "cwd": os.getcwd(),
        }
