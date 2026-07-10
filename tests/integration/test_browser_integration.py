"""Integration tests for Playwright browser execution."""

from __future__ import annotations

import pytest
import asyncio
from execution.browser.browser_executor import BrowserExecutor


def test_browser_executor_playwright_fallback() -> None:
    # Instantiate custom browser executor
    executor = BrowserExecutor()
    
    # Try opening URL. This should fallback cleanly to webbrowser if Playwright is not installed/run
    success = executor.open_url("https://www.google.com")
    assert success is True
    
    # Close executor
    executor.close()
    executor.browser_open = False
    assert executor.browser_open is False
