"""Planner agent: classify user intent và điều phối các agent/service."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from agents.browser_agent import BrowserAgent
from agents.memory_agent import MemoryAgent
from agents.vision_agent import VisionAgent
from services.llm_service import LLMService
from services.system_service import SystemService
from tools.clipboard_tool import read_clipboard, write_clipboard
from tools.file_reader import read_file


class PlannerAgent:
    def __init__(
        self,
        llm_service: LLMService | None = None,
        memory_agent: MemoryAgent | None = None,
        system_service: SystemService | None = None,
        browser_agent: BrowserAgent | None = None,
        vision_agent: VisionAgent | None = None,
    ) -> None:
        self.llm    = llm_service    or LLMService()
        self.memory = memory_agent   or MemoryAgent()
        self.system = system_service or SystemService()
        self.browser = browser_agent or BrowserAgent()
        self.vision  = vision_agent  or VisionAgent()

    # ─── Intent detection ────────────────────────────────────────────────────

    def detect_intent(self, text: str) -> dict[str, Any]:
        t = text.lower().strip()

        # Thời gian
        if re.search(r"(mấy giờ|bây giờ|thời gian|ngày mấy|hôm nay|mấy giờ|bây giờ)", t):
            return {"name": "time"}

        # Nhớ thông tin
        m = re.search(
            r"(?:nhớ|ghi nhớ|lưu|remember|note)\s+(?:rằng|là|that)?\s*(.+)", t
        )
        if m:
            return {"name": "remember", "value": m.group(1).strip()}

        # Nhớ lại
        if re.search(r"(nhớ lại|bạn nhớ|mình nhớ|recall|what do you know|bạn biết gì)", t):
            query = re.sub(r"nhớ lại|bạn nhớ|mình nhớ|recall|what do you know|bạn biết gì", "", t).strip()
            return {"name": "recall", "query": query}

        # Mở app (Chỉ chạy trực tiếp local nếu app_target khớp chính xác với alias đã khai báo hoặc tên đơn giản không dấu cách)
        m = re.search(
            r"(?:mở|open|khởi động|launch)\s+(.+?)(?:\s+cho mình|\s+giúp|\s+đi|$)", t
        )
        if m and not re.search(r"(http|www|\.com|trang)", t):
            app_target = m.group(1).strip()
            from agents.desktop_agent import DesktopAgent
            if app_target.lower() in DesktopAgent.APP_ALIASES or (" " not in app_target and len(app_target) < 15):
                return {"name": "open_app", "app": app_target}

        # Mở URL
        url_match = re.search(r"(https?://\S+|www\.\S+)", text)
        if url_match:
            return {"name": "open_url", "url": url_match.group(1)}

        # Thông tin hệ thống (Tránh trùng khớp với các lệnh tắt máy/khóa/khởi động lại)
        if re.search(r"(ram|cpu|bộ nhớ|máy tính|thông số|system info|cấu hình)", t):
            if not re.search(r"(tắt|khóa|khởi động lại|reset|shutdown|restart|hẹn giờ)", t):
                return {"name": "system_info"}

        # Hỏi về tài liệu (RAG)
        if re.search(r"(tài liệu|document|file|pdf|docx|sách|chương|nội dung)", t):
            return {"name": "rag_query", "query": text}

        return {"name": "llm_chat"}

    # ─── Main handler ────────────────────────────────────────────────────────

    async def handle_message(
        self, text: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        context = context or {}
        intent = self.detect_intent(text)

        # ── Thời gian ─────────────────────────────────────────────────────────
        if intent["name"] == "time":
            now = datetime.now()
            return self._response(
                f"Bây giờ là {now:%H:%M}, ngày {now:%d/%m/%Y}.",
                emotion="friendly", motion="nod",
            )

        # ── Ghi nhớ ──────────────────────────────────────────────────────────
        if intent["name"] == "remember":
            fact = self.memory.remember(intent["value"])
            return self._response(
                f"Mình đã ghi nhớ: {fact['text']}",
                emotion="friendly", motion="nod",
                memory={"stored": [fact]},
            )

        # ── Nhớ lại ──────────────────────────────────────────────────────────
        if intent["name"] == "recall":
            facts = self.memory.recall(intent.get("query", ""))
            if not facts:
                return self._response("Mình chưa có ghi nhớ nào phù hợp.", emotion="thinking")
            lines = "; ".join(item["text"] for item in facts[-5:])
            return self._response(f"Mình nhớ được: {lines}", emotion="friendly")

        # ── Mở app ────────────────────────────────────────────────────────────
        if intent["name"] == "open_app":
            result = await self.system.open_app(intent["app"])
            if result.get("success"):
                return self._response(
                    result.get("message", f"Mình đã mở {intent['app']}."),
                    emotion="excited", motion="nod",
                    actions=[{"type": "desktop.open_app", "status": "completed", "target": intent["app"]}],
                )
            return self._response(
                result.get("error", f"Mình chưa mở được {intent['app']}."),
                emotion="sad", motion="shake",
                actions=[{"type": "desktop.open_app", "status": "failed", "target": intent["app"]}],
            )

        # ── Mở URL ───────────────────────────────────────────────────────────
        if intent["name"] == "open_url":
            result = await self.browser.open_url(intent["url"])
            if result.get("success"):
                return self._response(f"Đã mở {intent['url']} trên trình duyệt.", emotion="friendly", motion="nod")
            return self._response(result.get("message", "Không mở được URL."), emotion="sad")

        # ── Tìm web ──────────────────────────────────────────────────────────
        if intent["name"] == "web_search":
            result = await self.browser.search(intent["query"])
            return self._response(
                result.get("message", "Không tìm được kết quả."),
                emotion="friendly" if result.get("success") else "sad",
            )

        # ── Clipboard ────────────────────────────────────────────────────────
        if intent["name"] == "clipboard_read":
            result = read_clipboard()
            if result.get("success"):
                preview = result["text"][:300]
                return self._response(f"Clipboard đang chứa:\n{preview}", emotion="friendly")
            return self._response("Không đọc được clipboard.", emotion="sad")

        # ── Đọc file ─────────────────────────────────────────────────────────
        if intent["name"] == "read_file":
            result = read_file(intent["path"])
            if result.get("success"):
                preview = result["text"][:500]
                trunc = " (đã cắt bớt)" if result.get("truncated") else ""
                return self._response(f"Nội dung file{trunc}:\n{preview}", emotion="focused")
            return self._response(result.get("error", "Không đọc được file."), emotion="sad")

        # ── Screen ───────────────────────────────────────────────────────────
        if intent["name"] == "screen_read":
            result = await self.vision.describe_screen()
            return self._response(
                result.get("message", "Không chụp được màn hình."),
                emotion="focused" if result.get("success") else "sad",
            )

        # ── System info ───────────────────────────────────────────────────────
        if intent["name"] == "system_info":
            result = await self.system.system_info()
            parts = [f"OS: {result.get('os')} {result.get('osVersion', '')}"]
            if "cpuPercent" in result:
                parts.append(f"CPU: {result['cpuPercent']}%")
            if "memoryPercent" in result:
                parts.append(f"RAM: {result['memoryPercent']}%")
            return self._response("\n".join(parts), emotion="friendly")

        # ── RAG query ─────────────────────────────────────────────────────────
        if intent["name"] == "rag_query":
            # RAG context đã được inject vào context["rag_context"] bởi main_server
            rag_context = context.get("rag_context", "")
            if not rag_context:
                # Không có tài liệu nào import → fallback LLM
                reply = await self.llm.chat(text, context)
                return self._response(reply, emotion="friendly")
            reply = await self.llm.chat(text, context)
            return self._response(reply, emotion="focused", motion="nod")

        # ── LLM fallback ─────────────────────────────────────────────────────
        reply = await self.llm.chat(text, context)
        return self._response(reply, emotion="friendly")

    # ─── Response builder ────────────────────────────────────────────────────

    def _response(
        self,
        text: str,
        emotion: str = "normal",
        motion: str = "idle",
        actions: list | None = None,
        memory: dict | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "assistant.response",
            "text": text,
            "emotion": emotion,
            "avatar": {"expression": emotion, "motion": motion, "lipsync": True},
        }
        if actions:
            result["actions"] = actions
        if memory:
            result["memory"] = memory
        return result