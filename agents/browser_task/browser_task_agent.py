"""Browser Task Automation Agent for IceGirl / DeskAgent.

Thực hiện tác vụ web nhiều bước tự động (đặt vé, tìm kiếm, điền form, v.v.)
Sử dụng playwright nếu có, fallback sang webbrowser + pyautogui.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.parse
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PLAYWRIGHT BACKEND (primary)
# ─────────────────────────────────────────────────────────────────────────────

class PlaywrightBackend:
    """Tự động hóa trình duyệt sử dụng Playwright."""

    def __init__(self) -> None:
        self._browser = None
        self._page = None
        self._playwright = None

    async def start(self, headless: bool = True) -> bool:
        """Khởi động trình duyệt. Trả về True nếu thành công."""
        try:
            from playwright.async_api import async_playwright  # type: ignore
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=headless)
            self._page = await self._browser.new_page()
            await self._page.set_viewport_size({"width": 1280, "height": 800})
            logger.info("[BrowserTask] Playwright browser started.")
            return True
        except ImportError:
            logger.warning("[BrowserTask] playwright chưa được cài đặt.")
            return False
        except Exception as exc:
            logger.error(f"[BrowserTask] Lỗi khởi động browser: {exc}")
            return False

    async def stop(self) -> None:
        """Đóng trình duyệt."""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._page = None

    async def navigate(self, url: str) -> dict:
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await self._page.title()
            return {"success": True, "url": url, "title": title}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def fill_input(self, selector: str, value: str) -> dict:
        try:
            await self._page.fill(selector, value)
            return {"success": True, "selector": selector, "value": value}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def click(self, selector: str) -> dict:
        try:
            await self._page.click(selector, timeout=10000)
            return {"success": True, "selector": selector}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def extract_text(self, selector: str = "body") -> dict:
        try:
            el = await self._page.query_selector(selector)
            text = await el.inner_text() if el else await self._page.inner_text("body")
            return {"success": True, "text": text[:3000]}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def screenshot(self, save_path: str | None = None) -> dict:
        try:
            if save_path is None:
                save_path = str(Path.home() / "Desktop" / f"icegirl_browser_{int(time.time())}.png")
            await self._page.screenshot(path=save_path, full_page=False)
            return {"success": True, "path": save_path}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def get_page_info(self) -> dict:
        try:
            url = self._page.url
            title = await self._page.title()
            return {"success": True, "url": url, "title": title}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> dict:
        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return {"success": True, "selector": selector}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def press_key(self, key: str) -> dict:
        try:
            await self._page.keyboard.press(key)
            return {"success": True, "key": key}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# BROWSER TASK AGENT
# ─────────────────────────────────────────────────────────────────────────────

class BrowserTaskAgent:
    """Agent thực hiện tác vụ trình duyệt đa bước.

    Nhận mô tả tác vụ bằng ngôn ngữ tự nhiên, dùng LLM để tạo kế hoạch
    và thực thi từng bước tuần tự.
    """

    STEP_TOOL_MAP = {
        "navigate": "navigate",
        "click": "click",
        "fill": "fill_input",
        "extract": "extract_text",
        "screenshot": "screenshot",
        "wait": "wait_for_selector",
        "press": "press_key",
        "search_google": "_search_google",
        "search_bing": "_search_bing",
    }

    def __init__(self, llm_service: Any = None) -> None:
        self._llm = llm_service
        self._backend: PlaywrightBackend | None = None

    async def _ensure_backend(self) -> bool:
        """Đảm bảo backend trình duyệt đã khởi động."""
        if self._backend is None or self._backend._browser is None:
            self._backend = PlaywrightBackend()
            return await self._backend.start(headless=True)
        return True

    async def _plan_steps(self, task_description: str) -> list[dict]:
        """Dùng LLM để tạo kế hoạch bước thực thi từ mô tả tác vụ."""
        system_prompt = (
            "Bạn là một agent tự động hóa trình duyệt. "
            "Hãy tạo danh sách các bước thực thi để hoàn thành tác vụ người dùng yêu cầu. "
            "Trả về JSON array với các bước theo định dạng:\n"
            '[{"step": 1, "action": "navigate|click|fill|extract|screenshot|wait|press|search_google|search_bing", '
            '"selector": "CSS selector hoặc null", "value": "giá trị hoặc URL hoặc null", '
            '"description": "mô tả bước này"}]\n'
            "Chỉ trả về JSON array, không có thêm text khác.\n"
            "Ví dụ actions:\n"
            "- navigate: mở URL (value = URL)\n"
            "- search_google: tìm kiếm Google (value = query)\n"
            "- search_bing: tìm kiếm Bing (value = query)\n"
            "- fill: điền form (selector = CSS selector, value = nội dung)\n"
            "- click: click element (selector = CSS selector)\n"
            "- extract: lấy text từ trang (selector = CSS selector hoặc null)\n"
            "- screenshot: chụp ảnh màn hình\n"
            "- wait: đợi element xuất hiện (selector = CSS selector)\n"
            "- press: nhấn phím (value = tên phím: Enter, Tab, Escape)"
        )

        if self._llm:
            try:
                response = await self._llm.chat_async(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Tác vụ: {task_description}"},
                    ],
                    temperature=0.1,
                )
                raw = response.strip()
                # Trích xuất JSON nếu có markdown code block
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                return json.loads(raw.strip())
            except Exception as exc:
                logger.error(f"[BrowserTask] LLM planning failed: {exc}")

        # Fallback: kế hoạch mặc định — tìm kiếm Google
        return [
            {"step": 1, "action": "search_google", "value": task_description, "selector": None, "description": f"Tìm kiếm: {task_description}"},
            {"step": 2, "action": "extract", "value": None, "selector": "body", "description": "Đọc kết quả trang"},
            {"step": 3, "action": "screenshot", "value": None, "selector": None, "description": "Chụp ảnh màn hình kết quả"},
        ]

    async def _execute_step(self, step: dict) -> dict:
        """Thực thi một bước trong kế hoạch."""
        action = step.get("action", "")
        selector = step.get("selector")
        value = step.get("value")

        if action == "navigate":
            return await self._backend.navigate(value or "https://google.com")
        elif action == "search_google":
            q = urllib.parse.quote_plus(value or "")
            return await self._backend.navigate(f"https://www.google.com/search?q={q}")
        elif action == "search_bing":
            q = urllib.parse.quote_plus(value or "")
            return await self._backend.navigate(f"https://www.bing.com/search?q={q}")
        elif action == "click":
            return await self._backend.click(selector or "body")
        elif action == "fill":
            return await self._backend.fill_input(selector or "input", value or "")
        elif action == "extract":
            return await self._backend.extract_text(selector or "body")
        elif action == "screenshot":
            return await self._backend.screenshot(value)
        elif action == "wait":
            return await self._backend.wait_for_selector(selector or "body")
        elif action == "press":
            return await self._backend.press_key(value or "Enter")
        else:
            return {"success": False, "error": f"Không nhận diện được action: '{action}'"}

    async def run_task(self, task_description: str, max_steps: int = 10) -> dict:
        """Thực hiện tác vụ web tự động từ mô tả ngôn ngữ tự nhiên.

        Args:
            task_description: Mô tả tác vụ, ví dụ 'tìm chuyến bay HAN-SGN ngày 15/8'.
            max_steps: Số bước tối đa được phép thực thi.

        Returns:
            Dict chứa kết quả từng bước và summary.
        """
        if not await self._ensure_backend():
            # Playwright không có — fallback: mở URL trong browser mặc định
            import webbrowser
            q = urllib.parse.quote_plus(task_description)
            url = f"https://www.google.com/search?q={q}"
            webbrowser.open(url)
            return {
                "success": True,
                "mode": "fallback_webbrowser",
                "summary": (
                    f"⚠️ Playwright chưa được cài đặt. Đã mở Google Search trong trình duyệt mặc định.\n"
                    f"🔗 Query: {task_description}\n"
                    f"Để tự động hoàn toàn, hãy cài đặt: pip install playwright && playwright install chromium"
                ),
                "steps": [],
            }

        # Lên kế hoạch
        steps = await self._plan_steps(task_description)
        steps = steps[:max_steps]

        step_results = []
        extracted_content = []

        try:
            for step in steps:
                step_num = step.get("step", "?")
                desc = step.get("description", step.get("action", ""))
                logger.info(f"[BrowserTask] Bước {step_num}: {desc}")

                result = await self._execute_step(step)
                result["step"] = step_num
                result["description"] = desc
                step_results.append(result)

                # Thu thập nội dung đã extract
                if step.get("action") == "extract" and result.get("text"):
                    extracted_content.append(result["text"])

                # Dừng nếu có lỗi nghiêm trọng
                if not result.get("success") and step.get("action") == "navigate":
                    logger.warning(f"[BrowserTask] Navigation failed at step {step_num}: {result.get('error')}")
                    break

                # Đợi giữa các bước
                await asyncio.sleep(0.8)

            # Chụp ảnh kết quả cuối
            final_shot = await self._backend.screenshot()
            page_info = await self._backend.get_page_info()

            summary_lines = [f"✅ Hoàn thành tác vụ: **{task_description}**"]
            summary_lines.append(f"📄 Trang hiện tại: {page_info.get('title', 'N/A')} — {page_info.get('url', '')}")
            summary_lines.append(f"🔢 Số bước đã thực thi: {len(step_results)}")
            if final_shot.get("path"):
                summary_lines.append(f"📸 Ảnh chụp màn hình: {final_shot['path']}")
            if extracted_content:
                summary_lines.append(f"\n📝 Nội dung thu thập:\n{extracted_content[0][:500]}...")

            return {
                "success": True,
                "mode": "playwright",
                "task": task_description,
                "steps_executed": len(step_results),
                "step_results": step_results,
                "screenshot_path": final_shot.get("path"),
                "extracted_content": extracted_content,
                "current_url": page_info.get("url"),
                "summary": "\n".join(summary_lines),
            }

        finally:
            await self._backend.stop()


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE RUNNER (cho tool registry)
# ─────────────────────────────────────────────────────────────────────────────

async def run_browser_task(task: str, headless: bool = True) -> dict:
    """Chạy tác vụ trình duyệt tự động — entry point cho tool registry.

    Args:
        task: Mô tả tác vụ bằng ngôn ngữ tự nhiên.
        headless: Nếu True, trình duyệt chạy ngầm (không hiển thị cửa sổ).

    Returns:
        Dict kết quả với summary và nội dung thu thập được.
    """
    try:
        from llm.manager import LLMService
        llm = LLMService()
    except Exception:
        llm = None

    agent = BrowserTaskAgent(llm_service=llm)
    return await agent.run_task(task)
