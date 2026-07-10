"""Browser automation execution layer using Playwright if available, falling back to webbrowser."""

from __future__ import annotations

import logging
import webbrowser
from typing import Any, Optional

logger = logging.getLogger("ai-companion.execution.browser")


class BrowserExecutor:
    """Browser automation execution layer using Playwright if available, falling back to webbrowser."""

    def __init__(self) -> None:
        self.browser_open = False
        self._playwright: Optional[Any] = None
        self._browser: Optional[Any] = None
        self._context: Optional[Any] = None
        self._page: Optional[Any] = None

    async def open_url_playwright(self, url: str) -> bool:
        """Open a URL using Playwright for automated interaction."""
        try:
            from playwright.async_api import async_playwright
            if not self._playwright:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
                self._context = await self._browser.new_context()
            
            self._page = await self._context.new_page()
            await self._page.goto(url, wait_until="networkidle", timeout=15000)
            self.browser_open = True
            logger.info("BrowserExecutor: Playwright opened and navigated to: %s", url)
            return True
        except Exception as e:
            logger.warning("Playwright failed to open URL (falling back to default browser): %s", e)
            return self.open_url_fallback(url)

    def open_url_fallback(self, url: str) -> bool:
        logger.info("BrowserExecutor: Opening URL in system default browser: %s", url)
        try:
            webbrowser.open(url)
            self.browser_open = True
            return True
        except Exception as e:
            logger.error("BrowserExecutor fallback failed to open URL: %s", e)
            return False

    def open_url(self, url: str) -> bool:
        # Check if playwright is available to run
        try:
            import playwright
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                # Run as a task in the background of the active event loop
                loop.create_task(self.open_url_playwright(url))
                self.browser_open = True
                return True
            except RuntimeError:
                # No running loop, run synchronously using asyncio.run
                try:
                    return asyncio.run(self.open_url_playwright(url))
                except Exception:
                    return self.open_url_fallback(url)
        except ImportError:
            return self.open_url_fallback(url)

    async def close_async(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning("Error closing Playwright browser: %s", e)
        finally:
            self._playwright = None
            self._browser = None
            self._context = None
            self._page = None
            self.browser_open = False

    def close(self) -> None:
        logger.info("BrowserExecutor: Closing browser")
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.close_async())
            except RuntimeError:
                self.browser_open = False
        except Exception:
            self.browser_open = False


# Global singleton
browser_executor = BrowserExecutor()
