"""Browser automation execution layer."""

from __future__ import annotations

import logging
import webbrowser

logger = logging.getLogger("ai-companion.execution.browser")


class BrowserExecutor:
    """Browser automation execution layer opening urls in system browser."""

    def __init__(self) -> None:
        self.browser_open = False

    def open_url(self, url: str) -> bool:
        logger.info("BrowserExecutor: Opening URL in system default browser: %s", url)
        try:
            webbrowser.open(url)
            self.browser_open = True
            return True
        except Exception as e:
            logger.error("BrowserExecutor failed to open URL: %s", e)
            return False

    def close(self) -> None:
        logger.info("BrowserExecutor: Closing browser")
        self.browser_open = False


# Global singleton
browser_executor = BrowserExecutor()
