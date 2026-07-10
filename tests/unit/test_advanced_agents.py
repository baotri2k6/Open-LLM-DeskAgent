"""Unit tests for Phase 7 — Advanced Autonomous Task Agents.

Tests cover:
- finance_tools: get_crypto_price, get_stock_price, get_market_overview, analyze_crypto, analyze_stock, compare_assets
- PlannerAgent: FINANCE_PATTERNS và BROWSER_TASK_PATTERNS intent detection
- BrowserTaskAgent: plan generation, step execution
"""

from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock, patch, AsyncMock
import unittest

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _make_binance_ticker(price: float = 65000.0, change_pct: float = 2.5) -> bytes:
    data = {
        "lastPrice": str(price),
        "priceChangePercent": str(change_pct),
        "highPrice": str(price * 1.05),
        "lowPrice": str(price * 0.95),
        "quoteVolume": "1500000000",
    }
    return json.dumps(data).encode()


def _make_yf_quote(price: float = 150.0, change_pct: float = 1.2) -> bytes:
    data = {
        "quoteResponse": {
            "result": [{
                "regularMarketPrice": price,
                "regularMarketChange": price * change_pct / 100,
                "regularMarketChangePercent": change_pct,
                "regularMarketVolume": 50000000,
                "fiftyTwoWeekHigh": price * 1.3,
                "fiftyTwoWeekLow": price * 0.7,
                "trailingPE": 28.5,
                "marketCap": 2_500_000_000_000,
                "shortName": "Apple Inc.",
            }]
        }
    }
    return json.dumps(data).encode()


def _make_yf_klines(closes: list[float]) -> bytes:
    """Mock Yahoo Finance chart endpoint."""
    timestamps = list(range(len(closes)))
    data = {
        "chart": {
            "result": [{
                "timestamp": timestamps,
                "indicators": {
                    "quote": [{
                        "close": closes,
                        "volume": [1_000_000] * len(closes),
                    }]
                }
            }]
        }
    }
    return json.dumps(data).encode()


# ─────────────────────────────────────────────────────────────────────────────
# FINANCE TOOLS TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestGetCryptoPrice(unittest.TestCase):
    """Test get_crypto_price using mocked Binance API."""

    def _run(self, symbol: str, response_bytes: bytes) -> dict:
        from io import BytesIO
        import urllib.request as _ur

        class _FakeResp:
            def read(self):
                return response_bytes
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        with patch.object(_ur, "urlopen", return_value=_FakeResp()):
            from tools.finance_tools import get_crypto_price
            return get_crypto_price(symbol)

    def test_btc_price_success(self):
        result = self._run("BTC", _make_binance_ticker(65000, 2.5))
        self.assertTrue(result["success"])
        self.assertAlmostEqual(result["price_usd"], 65000.0)
        self.assertAlmostEqual(result["change_24h_pct"], 2.5)
        self.assertIn("BTCUSDT", result["symbol"])

    def test_auto_append_usdt(self):
        """Symbol without USDT suffix should auto-append it."""
        result = self._run("ETH", _make_binance_ticker(3500, -1.2))
        self.assertTrue(result["success"])
        self.assertEqual(result["symbol"], "ETHUSDT")

    def test_invalid_symbol_returns_failure(self):
        from io import BytesIO
        import urllib.request as _ur

        class _FakeResp:
            def read(self):
                return b'{"msg":"Invalid symbol"}'
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        with patch.object(_ur, "urlopen", return_value=_FakeResp()):
            from tools.finance_tools import get_crypto_price
            result = get_crypto_price("FAKECOIN")
            self.assertFalse(result["success"])

    def test_network_error_returns_failure(self):
        import urllib.request as _ur
        with patch.object(_ur, "urlopen", side_effect=Exception("timeout")):
            from tools.finance_tools import get_crypto_price
            result = get_crypto_price("BTC")
            self.assertFalse(result["success"])


class TestGetStockPrice(unittest.TestCase):
    """Test get_stock_price using mocked Yahoo Finance API."""

    def _run(self, ticker: str, response_bytes: bytes) -> dict:
        import urllib.request as _ur

        class _FakeResp:
            def read(self):
                return response_bytes
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        with patch.object(_ur, "urlopen", return_value=_FakeResp()):
            from tools.finance_tools import get_stock_price
            return get_stock_price(ticker)

    def test_aapl_price_success(self):
        result = self._run("AAPL", _make_yf_quote(150.0, 1.2))
        self.assertTrue(result["success"])
        self.assertEqual(result["ticker"], "AAPL")
        self.assertEqual(result["price"], 150.0)
        self.assertIsNotNone(result["pe_ratio"])
        self.assertIn("Apple Inc.", result["name"])

    def test_ticker_uppercased(self):
        result = self._run("aapl", _make_yf_quote())
        self.assertTrue(result["success"])
        self.assertEqual(result["ticker"], "AAPL")

    def test_empty_result_returns_failure(self):
        empty = json.dumps({"quoteResponse": {"result": []}}).encode()
        result = self._run("INVALID", empty)
        self.assertFalse(result["success"])


class TestGetMarketOverview(unittest.TestCase):
    """Test get_market_overview."""

    def test_returns_multiple_coins(self):
        import urllib.request as _ur

        class _FakeResp:
            def __init__(self, data: bytes):
                self._data = data
            def read(self):
                return self._data
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        call_count = [0]
        fg_data = json.dumps({"data": [{"value": "72", "value_classification": "Greed"}]}).encode()

        def _fake_urlopen(req, timeout=10):
            idx = call_count[0]
            call_count[0] += 1
            if "alternative.me" in req.full_url:
                return _FakeResp(fg_data)
            return _FakeResp(_make_binance_ticker(65000 + idx * 100))

        with patch.object(_ur, "urlopen", side_effect=_fake_urlopen):
            from tools.finance_tools import get_market_overview
            result = get_market_overview()

        self.assertTrue(result["success"])
        self.assertIsInstance(result["coins"], list)
        self.assertGreater(len(result["coins"]), 0)


class TestRSICalculation(unittest.TestCase):
    """Test internal RSI helper function."""

    def test_rsi_overbought(self):
        from tools.finance_tools import _rsi
        closes = [100.0 + i * 3 for i in range(30)]  # Trending up
        rsi = _rsi(closes)
        self.assertGreater(rsi, 70)

    def test_rsi_oversold(self):
        from tools.finance_tools import _rsi
        closes = [100.0 - i * 3 for i in range(30)]  # Trending down
        rsi = _rsi(closes)
        self.assertLess(rsi, 30)

    def test_rsi_midrange(self):
        from tools.finance_tools import _rsi
        # Alternating ups and downs
        closes = [100.0 + (1 if i % 2 == 0 else -1) * 2 for i in range(30)]
        rsi = _rsi(closes)
        self.assertGreater(rsi, 30)
        self.assertLess(rsi, 70)


class TestCompareAssets(unittest.TestCase):
    """Test compare_assets."""

    def test_compare_multiple_coins(self):
        import urllib.request as _ur

        class _FakeResp:
            def read(self):
                return _make_binance_ticker()
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        with patch.object(_ur, "urlopen", return_value=_FakeResp()):
            from tools.finance_tools import compare_assets
            result = compare_assets(["BTC", "ETH"])
        self.assertTrue(result["success"])
        self.assertIn("assets", result)

    def test_string_input_parsed(self):
        """Comma-separated string should work."""
        import urllib.request as _ur

        class _FakeResp:
            def read(self):
                return _make_binance_ticker()
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        with patch.object(_ur, "urlopen", return_value=_FakeResp()):
            from tools.finance_tools import compare_assets
            result = compare_assets("BTC,ETH,SOL")
        self.assertTrue(result["success"])


# ─────────────────────────────────────────────────────────────────────────────
# PLANNER AGENT PATTERN TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestFinancePatternDetection(unittest.TestCase):
    """Test PlannerAgent.detect_intent recognizes finance intents."""

    @classmethod
    def setUpClass(cls):
        # Stub out heavyweight imports before importing PlannerAgent
        for mod in [
            "agents.browser.browser_agent",
            "agents.memory.memory_agent",
            "agents.vision.vision_agent",
            "llm.manager",
            "execution.windows.system_service",
            "tools.clipboard_tool",
            "tools.file_reader",
        ]:
            if mod not in sys.modules:
                sys.modules[mod] = MagicMock()

        from agents.planner.planner_agent import PlannerAgent
        cls.planner = PlannerAgent.__new__(PlannerAgent)

    def _intent(self, text: str) -> str:
        return self.planner.detect_intent(text)["name"]

    def test_btc_price_query(self):
        self.assertEqual(self._intent("giá bitcoin hôm nay là bao nhiêu?"), "finance_task")

    def test_crypto_price_direct(self):
        self.assertEqual(self._intent("ETH bao nhiêu tiền?"), "finance_task")

    def test_stock_price_query(self):
        self.assertEqual(self._intent("giá cổ phiếu AAPL là bao nhiêu?"), "finance_task")

    def test_market_overview(self):
        self.assertEqual(self._intent("thị trường crypto hôm nay thế nào?"), "finance_task")

    def test_technical_analysis(self):
        self.assertEqual(self._intent("phân tích kỹ thuật BTC cho tớ"), "finance_task")

    def test_rsi_query(self):
        self.assertEqual(self._intent("RSI của ETH đang ở mức nào?"), "finance_task")

    def test_compare_assets(self):
        self.assertEqual(self._intent("so sánh BTC và ETH cho tớ"), "finance_task")

    def test_nasdaq_stock(self):
        self.assertEqual(self._intent("nvidia cổ phiếu hôm nay tăng giảm ra sao?"), "finance_task")


class TestBrowserTaskPatternDetection(unittest.TestCase):
    """Test PlannerAgent.detect_intent recognizes browser automation intents."""

    @classmethod
    def setUpClass(cls):
        for mod in [
            "agents.browser.browser_agent",
            "agents.memory.memory_agent",
            "agents.vision.vision_agent",
            "llm.manager",
            "execution.windows.system_service",
            "tools.clipboard_tool",
            "tools.file_reader",
        ]:
            if mod not in sys.modules:
                sys.modules[mod] = MagicMock()

        from agents.planner.planner_agent import PlannerAgent
        cls.planner = PlannerAgent.__new__(PlannerAgent)

    def _intent(self, text: str) -> str:
        return self.planner.detect_intent(text)["name"]

    def test_book_flight(self):
        self.assertEqual(self._intent("đặt vé máy bay từ HAN đến SGN ngày 15/8"), "browser_task")

    def test_search_flight(self):
        self.assertEqual(self._intent("tìm chuyến bay giá rẻ từ Hà Nội đi Đà Nẵng"), "browser_task")

    def test_auto_fill_form(self):
        self.assertEqual(self._intent("điền form đăng ký online cho tớ"), "browser_task")

    def test_auto_browser_task(self):
        self.assertEqual(self._intent("tự động thực hiện tác vụ trên web"), "browser_task")

    def test_book_ticket(self):
        self.assertEqual(self._intent("đặt vé xem phim tối nay"), "browser_task")


# ─────────────────────────────────────────────────────────────────────────────
# BROWSER TASK AGENT TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestBrowserTaskAgent(unittest.TestCase):
    """Test BrowserTaskAgent plan and fallback behavior."""

    def test_plan_steps_fallback_no_llm(self):
        """Without LLM, should return default 3-step search plan."""
        import asyncio
        from agents.browser_task.browser_task_agent import BrowserTaskAgent
        agent = BrowserTaskAgent(llm_service=None)
        steps = asyncio.get_event_loop().run_until_complete(
            agent._plan_steps("tìm chuyến bay HAN-SGN")
        )
        self.assertIsInstance(steps, list)
        self.assertGreater(len(steps), 0)
        # First step should be a search
        actions = [s["action"] for s in steps]
        self.assertTrue(any(a in ("search_google", "search_bing", "navigate") for a in actions))

    def test_run_task_playwright_unavailable_returns_fallback(self):
        """When playwright not installed, should gracefully fallback."""
        import asyncio
        from agents.browser_task.browser_task_agent import BrowserTaskAgent

        agent = BrowserTaskAgent(llm_service=None)

        # Mock _ensure_backend to return False (playwright unavailable)
        async def _no_backend():
            return False
        agent._ensure_backend = _no_backend

        # Mock webbrowser.open
        import webbrowser
        with patch.object(webbrowser, "open", return_value=True):
            result = asyncio.get_event_loop().run_until_complete(
                agent.run_task("tìm chuyến bay HAN-SGN")
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "fallback_webbrowser")
        self.assertIn("playwright", result["summary"].lower())

    def test_step_execute_search_google(self):
        """Verify search_google step creates correct URL."""
        import asyncio
        from agents.browser_task.browser_task_agent import BrowserTaskAgent

        agent = BrowserTaskAgent()
        backend_mock = MagicMock()
        backend_mock.navigate = AsyncMock(return_value={"success": True, "title": "Google", "url": "https://google.com"})
        agent._backend = backend_mock

        step = {"action": "search_google", "value": "chuyến bay HAN SGN", "selector": None}
        result = asyncio.get_event_loop().run_until_complete(agent._execute_step(step))

        self.assertTrue(result["success"])
        call_url = backend_mock.navigate.call_args[0][0]
        self.assertIn("google.com/search", call_url)
        self.assertIn("chuy", call_url)  # URL-encoded query present


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY TOOLS SCHEMA TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistryToolsRegistered(unittest.TestCase):
    """Verify all new tools are registered in the central tool registry."""

    @classmethod
    def setUpClass(cls):
        # Stub out complex dependencies before importing registry
        cls._original_modules = {}
        for mod in [
            "agents.coding.coding_agent",
            "agents.subagent_service",
            "skills.skills_manager",
            "agents.browser_task.browser_task_agent",
            "tools.finance_tools",
            "plugins.plugin_manager",
        ]:
            if mod in sys.modules:
                cls._original_modules[mod] = sys.modules[mod]
            else:
                cls._original_modules[mod] = None
            sys.modules[mod] = MagicMock()

    @classmethod
    def tearDownClass(cls):
        # Restore sys.modules to clean up mock leak
        for mod, val in cls._original_modules.items():
            if val is None:
                if mod in sys.modules:
                    del sys.modules[mod]
            else:
                sys.modules[mod] = val

    def test_finance_tools_registered(self):
        from tools.registry import TOOL_REGISTRY
        expected = [
            "get_crypto_price",
            "get_stock_price",
            "get_market_overview",
            "analyze_crypto",
            "analyze_stock",
            "compare_assets",
        ]
        for name in expected:
            self.assertIn(name, TOOL_REGISTRY, f"Tool '{name}' not found in registry")

    def test_browser_task_registered(self):
        from tools.registry import TOOL_REGISTRY
        self.assertIn("run_browser_task", TOOL_REGISTRY)

    def test_tool_schemas_have_required_fields(self):
        from tools.registry import TOOL_REGISTRY
        for tool_name in ["get_crypto_price", "get_stock_price", "analyze_stock", "run_browser_task"]:
            if tool_name in TOOL_REGISTRY:
                schema = TOOL_REGISTRY[tool_name].schema
                self.assertIn("name", schema, f"{tool_name} schema missing 'name'")
                self.assertIn("description", schema, f"{tool_name} schema missing 'description'")
                self.assertIn("parameters", schema, f"{tool_name} schema missing 'parameters'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
