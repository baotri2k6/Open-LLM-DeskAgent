"""Planner agent: classify user intent và điều phối các agent/service."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from agents.browser.browser_agent import BrowserAgent
from agents.memory.memory_agent import MemoryAgent
from agents.vision.vision_agent import VisionAgent
from llm.manager import LLMService
from execution.windows.system_service import SystemService
from tools.clipboard_tool import read_clipboard, write_clipboard
from tools.file_reader import read_file


CODING_PATTERNS = [
    r"(sửa|fix|debug|vá)\s+(bug|lỗi|error|vấn đề|issue)",
    r"(sửa|fix)\s+(code|file)",
    r"(thêm|add|implement|tạo)\s+(tính năng|feature|chức năng|function|class|module)",
    r"(refactor|tái cấu trúc|clean|dọn)\s+(code|file|module)",
    r"(đọc|xem|check|kiểm tra)\s+(code|file|dự án|project)",
    r"(viết|write|tạo)\s+(code|script|function|class)",
    r"(chạy|run|test|kiểm thử)\s+(test|pytest|unittest)",
    r"vào\s+(code|terminal|file)\s+(sửa|fix|đọc)",
]

FINANCE_PATTERNS = [
    r"(giá|price|giá hiện tại)\s+(bitcoin|btc|eth|ethereum|crypto|coin|đồng)",
    r"(bitcoin|btc|eth|ethereum|bnb|sol|xrp|ada|doge|avax|matic)\s+(giá|là bao nhiêu|hôm nay|bao nhiêu)",
    r"(btc|eth|bnb|sol|xrp|ada|doge|avax|matic)\s+(bao nhiêu|giá|tăng|giảm)",
    r"(giá|price)\s+(cổ phiếu|stock|share|mã cổ phiếu)",
    r"cổ phiếu\s+\w+\s*(giá|hôm nay|bao nhiêu|tăng|giảm)",
    r"(cổ phiếu|stock)\s+(hôm nay|tăng|giảm|bao nhiêu)",
    r"(thị trường|market)\s+(hôm nay|đang|crypto|chứng khoán)",
    r"(crypto|bitcoin|ethereum|chứng khoán)\s+(hôm nay|thế nào|đang)",
    r"(phân tích|analyze|xác định)\s+(kỹ thuật|technical|cổ phiếu|coin|crypto|btc|eth)",
    r"(rsi|ma20|ma50|golden cross|death cross|tín hiệu mua|tín hiệu bán)",
    r"(fear|greed|chỉ số|index)\s*(and|&|và)\s*(greed|fear)?",
    r"(so sánh|compare)\s+(btc|eth|coin|cổ phiếu|tiền|tài sản)",
    r"(apple|aapl|nvda|nvidia|msft|microsoft|google|googl|amzn|amazon|tesla|tsla)\s*(giá|stock|cổ phiếu|hôm nay)?",
    r"(vic|vhm|hpg|vnm|bvh|fpt|ssi|msn)\.vn",
]

BROWSER_TASK_PATTERNS = [
    r"(đặt|đặt mua|book|bảo lưu)\s+(vé|chỗ|điềm)",
    r"(tìm|search|kiếm)\s+(chuyến bay|vé máy bay|vé xe|vé tàu|phiến bay)",
    r"(tự động|auto)\s+(mở|tìm|click|điền|thực hiện)\s+(trên|trang|web)",
    r"(mua hàng|order|thanh toán|checkout)\s+(trên|từ)\s+\S+",
    r"(điền form|điền mẫu|đăng ký online|submit|gửi)",
    r"(web browser|trình duyệt)\s+(tự động|auto|thực hiện)",
    r"(thực hiện|hoàn thành|làm)\s+(tác vụ|task)\s+(trên|online|web)",
]

import re as _re

def _is_coding_task(text: str) -> bool:
    t = text.lower()
    return any(_re.search(p, t) for p in CODING_PATTERNS)

def _is_finance_task(text: str) -> bool:
    t = text.lower()
    return any(_re.search(p, t) for p in FINANCE_PATTERNS)

def _is_browser_task(text: str) -> bool:
    t = text.lower()
    return any(_re.search(p, t) for p in BROWSER_TASK_PATTERNS)



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

        # Phân tích tài chính — kiểm tra TRƯỚC time để tránh "hôm nay" bị match sai
        if _is_finance_task(text):
            return {"name": "finance_task", "query": text}

        # Tác vụ trình duyệt tự động
        if _is_browser_task(text):
            return {"name": "browser_task", "task": text}

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
            from agents.desktop.desktop_agent import DesktopAgent
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

        if _is_coding_task(text):
            return {"name": "coding_task", "task": text}

        # Hỏi về tài liệu (RAG)
        if re.search(r"(tài liệu|document|file|pdf|docx|sách|chương|nội dung)", t):
            return {"name": "rag_query", "query": text}

        return {"name": "llm_chat"}

    # ─── Main handler ────────────────────────────────────────────────────────

    async def handle_message(
        self, text: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        context = context or {}
        
        # ─── Load and Inject Beliefs ──────────────────────────────────────────
        try:
            from belief.belief_store import belief_store
            beliefs = belief_store.list_all_beliefs()
            active_beliefs = [b for b in beliefs if b.confidence >= 0.5]
            if active_beliefs:
                context["beliefs"] = [
                    {"key": b.key, "value": b.value, "confidence": b.confidence}
                    for b in active_beliefs
                ]
                
                # Check if the requested intent depends on a broken tool
                intent = self.detect_intent(text)
                intent_name = intent["name"]
                
                intent_tool_map = {
                    "open_url": "open_url",
                    "web_search": "search_google",
                    "read_file": "read_file",
                    "screen_read": "click_element_by_vision",
                }
                
                t_lower = text.lower()
                is_shell_req = intent_name == "open_app" or "command" in t_lower or "chạy lệnh" in t_lower
                
                broken_tool = None
                for b in active_beliefs:
                    if b.key.startswith("env.tool_broken.") and b.value == "true":
                        tool_name = b.key.split("env.tool_broken.")[-1]
                        if intent_name in intent_tool_map and intent_tool_map[intent_name] == tool_name:
                            broken_tool = tool_name
                            break
                        if is_shell_req and tool_name == "execute_command":
                            broken_tool = "execute_command"
                            break
                
                if broken_tool:
                    import logging
                    logging.getLogger("ai-companion.planner").warning(
                        "PlannerAgent: Blocked execution of %s because it is marked broken in BeliefStore",
                        broken_tool
                    )
                    return self._response(
                        f"Mình nhận thấy công cụ `{broken_tool}` hiện đang bị lỗi trong môi trường này (dựa trên nhật ký tự kiểm điểm). Bạn có muốn mình thử phương án khác không?",
                        emotion="sad", motion="shake"
                    )
        except Exception as e:
            import logging
            logging.getLogger("ai-companion.planner").warning("PlannerAgent failed to process/inject beliefs: %s", e)

        intent = self.detect_intent(text)
        intent_name = intent["name"]
        
        response_dict = None

        # ── Thời gian ─────────────────────────────────────────────────────────
        if intent["name"] == "time":
            now = datetime.now()
            response_dict = self._response(
                f"Bây giờ là {now:%H:%M}, ngày {now:%d/%m/%Y}.",
                emotion="friendly", motion="nod",
            )

        # ── Ghi nhớ ──────────────────────────────────────────────────────────
        elif intent["name"] == "remember":
            fact = self.memory.remember(intent["value"])
            response_dict = self._response(
                f"Mình đã ghi nhớ: {fact['text']}",
                emotion="friendly", motion="nod",
                memory={"stored": [fact]},
            )

        # ── Nhớ lại ──────────────────────────────────────────────────────────
        elif intent["name"] == "recall":
            facts = self.memory.recall(intent.get("query", ""))
            if not facts:
                response_dict = self._response("Mình chưa có ghi nhớ nào phù hợp.", emotion="thinking")
            else:
                lines = "; ".join(item["text"] for item in facts[-5:])
                response_dict = self._response(f"Mình nhớ được: {lines}", emotion="friendly")

        # ── Mở app ────────────────────────────────────────────────────────────
        elif intent["name"] == "open_app":
            result = await self.system.open_app(intent["app"])
            if result.get("success"):
                response_dict = self._response(
                    result.get("message", f"Mình đã mở {intent['app']}."),
                    emotion="excited", motion="nod",
                    actions=[{"type": "desktop.open_app", "status": "completed", "target": intent["app"]}],
                )
            else:
                response_dict = self._response(
                    result.get("error", f"Mình chưa mở được {intent['app']}."),
                    emotion="sad", motion="shake",
                    actions=[{"type": "desktop.open_app", "status": "failed", "target": intent["app"]}],
                )

        # ── Mở URL ───────────────────────────────────────────────────────────
        elif intent["name"] == "open_url":
            result = await self.browser.open_url(intent["url"])
            if result.get("success"):
                response_dict = self._response(f"Đã mở {intent['url']} trên trình duyệt.", emotion="friendly", motion="nod")
            else:
                response_dict = self._response(result.get("message", "Không mở được URL."), emotion="sad")

        # ── Tìm web ──────────────────────────────────────────────────────────
        elif intent["name"] == "web_search":
            result = await self.browser.search(intent["query"])
            response_dict = self._response(
                result.get("message", "Không tìm được kết quả."),
                emotion="friendly" if result.get("success") else "sad",
            )

        # ── Clipboard ────────────────────────────────────────────────────────
        elif intent["name"] == "clipboard_read":
            result = read_clipboard()
            if result.get("success"):
                preview = result["text"][:300]
                response_dict = self._response(f"Clipboard đang chứa:\n{preview}", emotion="friendly")
            else:
                response_dict = self._response("Không đọc được clipboard.", emotion="sad")

        # ── Đọc file ─────────────────────────────────────────────────────────
        elif intent["name"] == "read_file":
            result = read_file(intent["path"])
            if result.get("success"):
                preview = result["text"][:500]
                trunc = " (đã cắt bớt)" if result.get("truncated") else ""
                response_dict = self._response(f"Nội dung file{trunc}:\n{preview}", emotion="focused")
            else:
                response_dict = self._response(result.get("error", "Không đọc được file."), emotion="sad")

        # ── Screen ───────────────────────────────────────────────────────────
        elif intent["name"] == "screen_read":
            result = await self.vision.describe_screen()
            response_dict = self._response(
                result.get("message", "Không chụp được màn hình."),
                emotion="focused" if result.get("success") else "sad",
            )

        # ── System info ───────────────────────────────────────────────────────
        elif intent["name"] == "system_info":
            result = await self.system.system_info()
            parts = [f"OS: {result.get('os')} {result.get('osVersion', '')}"]
            if "cpuPercent" in result:
                parts.append(f"CPU: {result['cpuPercent']}%")
            if "memoryPercent" in result:
                parts.append(f"RAM: {result['memoryPercent']}%")
            response_dict = self._response("\n".join(parts), emotion="friendly")

        # ── RAG query ─────────────────────────────────────────────────────────
        elif intent["name"] == "rag_query":
            # RAG context đã được inject vào context["rag_context"] bởi main_server
            rag_context = context.get("rag_context", "")
            if not rag_context:
                # Không có tài liệu nào import → fallback LLM
                reply = await self.llm.chat(text, context)
                response_dict = self._response(reply, emotion="friendly")
            else:
                reply = await self.llm.chat(text, context)
                response_dict = self._response(reply, emotion="focused", motion="nod")

        # ── Coding Task ───────────────────────────────────────────────────────
        elif intent["name"] == "coding_task":
            from agents.coding.coding_agent import run_coding_task
            result = await run_coding_task(intent["task"])
            if result.get("success"):
                response_dict = self._response(
                    f"Mình đã hoàn thành sửa code thành công!\nTóm tắt: {result.get('summary')}",
                    emotion="excited", motion="nod"
                )
            else:
                response_dict = self._response(
                    f"Mình đã thử sửa code nhưng chưa thành công.\nChi tiết: {result.get('summary')}",
                    emotion="sad", motion="shake"
                )

        # ── Finance Task ────────────────────────────────────────────────────────────
        elif intent["name"] == "finance_task":
            result = await self._handle_finance_query(text)
            response_dict = self._response(
                result.get("summary", "Không lấy được dữ liệu tài chính."),
                emotion="focused" if result.get("success") else "sad",
                motion="nod" if result.get("success") else "shake",
            )

        # ── Browser Task ──────────────────────────────────────────────────────────
        elif intent["name"] == "browser_task":
            from agents.browser_task.browser_task_agent import run_browser_task
            result = await run_browser_task(intent["task"])
            response_dict = self._response(
                result.get("summary", "Không thực hiện được tác vụ trên trình duyệt."),
                emotion="excited" if result.get("success") else "sad",
                motion="nod" if result.get("success") else "shake",
            )

        # ── LLM fallback ─────────────────────────────────────────────────────
        else:
            reply = await self.llm.chat(text, context)
            response_dict = self._response(reply, emotion="friendly")

        # Wire learning_manager trigger on planner_agent task completion
        try:
            from learning.learning_manager import learning_manager
            success = True
            if response_dict.get("emotion") == "sad" or "failed" in response_dict.get("text", "").lower() or "không" in response_dict.get("text", "").lower():
                success = False
            learning_manager.process_task_outcome(
                task_id=f"planner_task_{intent_name}",
                success=success,
                feedback=response_dict.get("text", "Processed successfully")
            )
        except Exception:
            pass

        return response_dict

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

    # ─── Finance Query Dispatcher ────────────────────────────────────────────────────────────

    async def _handle_finance_query(self, text: str) -> dict:
        """Phân tích yêu cầu tài chính và gọi đúng tool tương ứng."""
        import re as _r
        from tools.finance_tools import (
            get_crypto_price, get_stock_price, get_market_overview,
            analyze_crypto, analyze_stock, compare_assets,
        )

        t = text.lower()

        # Tổng quan thị trường
        if _r.search(r"(thị trường|market|tổng quan|overview)", t):
            return get_market_overview()

        # So sánh tài sản
        if _r.search(r"(so sánh|compare)", t):
            # Trích xuất các ký hiệu từ văn bản
            candidates = _r.findall(r"\b([A-Z]{2,6}(?:\.VN)?|bitcoin|ethereum|bnb|sol|xrp|ada)\b", text, _r.IGNORECASE)
            tickers = [c.upper() for c in candidates]
            if tickers:
                return compare_assets(tickers)

        # Phân tích kỹ thuật
        if _r.search(r"(phân tích|analyze|rsi|ma20|ma50|technical)", t):
            # Crypto
            m = _r.search(r"\b(btc|eth|bnb|sol|xrp|ada|doge|avax|matic|bitcoin|ethereum)\b", t)
            if m:
                sym = m.group(1).upper()
                sym_map = {"BITCOIN": "BTC", "ETHEREUM": "ETH"}
                sym = sym_map.get(sym, sym)
                return analyze_crypto(sym)
            # Stock
            m = _r.search(r"\b([A-Z]{2,6}(?:\.VN)?)\b", text)
            if m:
                return analyze_stock(m.group(1).upper())

        # Giá crypto
        crypto_map = {
            "bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH",
            "bnb": "BNB", "sol": "SOL", "xrp": "XRP", "ada": "ADA",
            "doge": "DOGE", "avax": "AVAX", "matic": "MATIC", "dot": "DOT",
        }
        for keyword, sym in crypto_map.items():
            if keyword in t:
                return get_crypto_price(sym)

        # Giá cổ phiếu
        m = _r.search(r"\b([A-Z]{2,6}(?:\.VN)?)\b", text)
        if m:
            ticker_candidate = m.group(1).upper()
            # Bỏ qua các từ khóa phổ biến không phải mã cổ phiếu
            skip = {"AI", "OK", "CEO", "API", "URL", "HTTP", "HTTPS", "RAM", "CPU", "GPU"}
            if ticker_candidate not in skip:
                return get_stock_price(ticker_candidate)

        # Fallback: tổng quan thị trường
        return get_market_overview()