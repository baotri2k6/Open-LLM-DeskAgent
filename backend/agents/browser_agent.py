"""Browser agent — tìm kiếm web và mở URL."""

from __future__ import annotations

from tools.web_search import search_web
from tools.browser_control import open_url, search_google


class BrowserAgent:
    async def search(self, query: str) -> dict:
        from tools.browser_control import search_google
        result = search_google(query)
        if result["success"]:
            return {
                "success": True,
                "message": f"Mình đã mở trình duyệt để tìm kiếm '{query}' trên Google cho bạn.",
            }
        return {
            "success": False,
            "message": f"Không mở được trình duyệt để tìm kiếm: {result.get('error', 'lỗi không xác định')}",
        }

    async def open_url(self, url: str) -> dict:
        result = open_url(url)
        if result["success"]:
            return {"success": True, "message": f"Đã mở {result['url']}."}
        return {"success": False, "message": result.get("error", "Không mở được URL.")}

    async def open_google(self, query: str) -> dict:
        result = search_google(query)
        if result["success"]:
            return {"success": True, "message": f"Đã mở Google tìm '{query}'."}
        return {"success": False, "message": result.get("error")}