"""Financial Intelligence Tools for IceGirl / DeskAgent.

Cung cấp dữ liệu thị trường tài chính theo thời gian thực và phân tích kỹ thuật
mà KHÔNG yêu cầu API key — sử dụng Yahoo Finance và Binance public endpoints.
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _http_get(url: str, timeout: int = 10) -> dict | list | None:
    """Gửi GET request và trả về JSON đã parse. Trả về None nếu thất bại."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _pct_change(old: float, new: float) -> float:
    """Tính phần trăm thay đổi."""
    if old == 0:
        return 0.0
    return round((new - old) / old * 100, 2)


def _rsi(closes: list[float], period: int = 14) -> float:
    """Tính RSI (Relative Strength Index)."""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def _sma(values: list[float], period: int) -> float | None:
    """Simple Moving Average."""
    if len(values) < period:
        return None
    return round(sum(values[-period:]) / period, 4)


# ─────────────────────────────────────────────────────────────────────────────
# CRYPTO TOOLS (Binance Public API — không cần API key)
# ─────────────────────────────────────────────────────────────────────────────

BINANCE_BASE = "https://api.binance.com/api/v3"


def get_crypto_price(symbol: str) -> dict:
    """Lấy giá tiền điện tử theo thời gian thực từ Binance.

    Args:
        symbol: Ký hiệu cặp giao dịch, ví dụ 'BTC', 'ETH', 'BNB'.
                Tự động thêm 'USDT' nếu không có.

    Returns:
        Dict chứa giá hiện tại, thay đổi 24h, khối lượng giao dịch.
    """
    sym = symbol.upper().strip()
    # Nếu chưa phải cặp giao dịch, thêm USDT làm quote currency
    if not sym.endswith("USDT"):
        sym = sym + "USDT"

    ticker = _http_get(f"{BINANCE_BASE}/ticker/24hr?symbol={sym}")
    if not ticker or "lastPrice" not in ticker:
        return {
            "success": False,
            "error": f"Không tìm thấy dữ liệu cho '{sym}'. Kiểm tra lại ký hiệu (ví dụ: BTC, ETH, SOL, ADA).",
        }

    price = float(ticker["lastPrice"])
    change_pct = float(ticker["priceChangePercent"])
    high = float(ticker["highPrice"])
    low = float(ticker["lowPrice"])
    volume_usdt = float(ticker["quoteVolume"])

    trend = "📈 Tăng" if change_pct > 0 else ("📉 Giảm" if change_pct < 0 else "➡️ Đi ngang")

    return {
        "success": True,
        "symbol": sym,
        "price_usd": price,
        "change_24h_pct": change_pct,
        "high_24h": high,
        "low_24h": low,
        "volume_24h_usdt": round(volume_usdt, 2),
        "trend": trend,
        "summary": (
            f"{sym}: ${price:,.4f} ({change_pct:+.2f}%) | "
            f"24h High: ${high:,.4f} | Low: ${low:,.4f} | "
            f"Khối lượng: ${volume_usdt:,.0f} USDT"
        ),
    }


def get_market_overview() -> dict:
    """Lấy tổng quan thị trường: BTC, ETH, BNB và chỉ số Fear & Greed."""
    coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    results = []
    for coin in coins:
        t = _http_get(f"{BINANCE_BASE}/ticker/24hr?symbol={coin}")
        if t and "lastPrice" in t:
            pct = float(t["priceChangePercent"])
            arrow = "▲" if pct > 0 else "▼"
            results.append({
                "symbol": coin.replace("USDT", ""),
                "price": float(t["lastPrice"]),
                "change_pct": pct,
                "arrow": arrow,
            })

    # Fear & Greed Index
    fg = _http_get("https://api.alternative.me/fng/?limit=1")
    fear_greed = None
    if fg and "data" in fg and fg["data"]:
        fg_data = fg["data"][0]
        fear_greed = {
            "value": int(fg_data["value"]),
            "classification": fg_data["value_classification"],
        }

    lines = ["📊 **Tổng quan thị trường Crypto:**"]
    for r in results:
        lines.append(f"  • {r['symbol']}: ${r['price']:,.2f} {r['arrow']} {r['change_pct']:+.2f}%")
    if fear_greed:
        lines.append(f"\n😱 Fear & Greed Index: **{fear_greed['value']}** — {fear_greed['classification']}")

    return {
        "success": True,
        "coins": results,
        "fear_greed": fear_greed,
        "summary": "\n".join(lines),
    }


def analyze_crypto(symbol: str, interval: str = "1d", limit: int = 50) -> dict:
    """Phân tích kỹ thuật cho một cặp crypto: RSI, MA20, MA50, tín hiệu.

    Args:
        symbol: Ký hiệu, ví dụ 'BTC', 'ETH'.
        interval: Khung thời gian nến ('1h', '4h', '1d', '1w').
        limit: Số nến lấy về (tối đa 500).
    """
    sym = symbol.upper().strip()
    if not sym.endswith("USDT"):
        sym = sym + "USDT"

    klines = _http_get(
        f"{BINANCE_BASE}/klines?symbol={sym}&interval={interval}&limit={limit}"
    )
    if not klines or not isinstance(klines, list):
        return {"success": False, "error": f"Không lấy được dữ liệu nến cho {sym}."}

    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    current_price = closes[-1]
    ma20 = _sma(closes, 20)
    ma50 = _sma(closes, 50)
    rsi_val = _rsi(closes)

    # Xác định tín hiệu giao dịch đơn giản
    signals = []
    if rsi_val < 30:
        signals.append("🟢 RSI quá bán — có thể mua")
    elif rsi_val > 70:
        signals.append("🔴 RSI quá mua — thận trọng")

    if ma20 and current_price > ma20:
        signals.append("🟢 Giá trên MA20 — xu hướng tích cực ngắn hạn")
    elif ma20:
        signals.append("🔴 Giá dưới MA20 — xu hướng tiêu cực ngắn hạn")

    if ma50 and ma20 and ma20 > ma50:
        signals.append("🟢 MA20 cắt lên MA50 — tín hiệu Golden Cross")
    elif ma50 and ma20 and ma20 < ma50:
        signals.append("🔴 MA20 dưới MA50 — tín hiệu Death Cross")

    avg_volume = sum(volumes[-10:]) / 10 if len(volumes) >= 10 else None

    return {
        "success": True,
        "symbol": sym,
        "interval": interval,
        "current_price": current_price,
        "ma20": ma20,
        "ma50": ma50,
        "rsi": rsi_val,
        "avg_volume_10": round(avg_volume, 2) if avg_volume else None,
        "signals": signals,
        "summary": (
            f"📊 Phân tích {sym} ({interval}):\n"
            f"  Giá hiện tại: ${current_price:,.4f}\n"
            f"  MA20: ${ma20:,.4f}" if ma20 else ""
            f"  MA50: ${ma50:,.4f}" if ma50 else ""
            f"\n  RSI({len(closes)}): {rsi_val}\n"
            + ("\n".join(f"  {s}" for s in signals) if signals else "  Không có tín hiệu rõ ràng")
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# STOCK TOOLS (Yahoo Finance — không cần API key)
# ─────────────────────────────────────────────────────────────────────────────

YF_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
YF_QUOTE = "https://query1.finance.yahoo.com/v7/finance/quote"


def get_stock_price(ticker: str) -> dict:
    """Lấy giá cổ phiếu hiện tại từ Yahoo Finance.

    Args:
        ticker: Mã cổ phiếu, ví dụ 'AAPL', 'VIC.VN', 'MSFT', 'NVDA'.
                Cổ phiếu Việt Nam thêm '.VN' (ví dụ: VIC.VN, VNM.VN).

    Returns:
        Dict chứa giá hiện tại, thay đổi, P/E, volume.
    """
    sym = ticker.upper().strip()
    data = _http_get(
        f"{YF_QUOTE}?symbols={urllib.parse.quote(sym)}&fields=regularMarketPrice,"
        f"regularMarketChange,regularMarketChangePercent,regularMarketVolume,"
        f"fiftyTwoWeekHigh,fiftyTwoWeekLow,trailingPE,marketCap,shortName",
        timeout=12,
    )
    if not data:
        return {"success": False, "error": f"Không kết nối được Yahoo Finance cho '{sym}'."}

    try:
        result = data["quoteResponse"]["result"]
        if not result:
            return {
                "success": False,
                "error": (
                    f"Không tìm thấy '{sym}'. "
                    "Thử lại với mã chính xác hơn (ví dụ: AAPL, MSFT, VIC.VN)."
                ),
            }
        q = result[0]
        price = q.get("regularMarketPrice", 0)
        change = q.get("regularMarketChange", 0)
        change_pct = q.get("regularMarketChangePercent", 0)
        volume = q.get("regularMarketVolume", 0)
        high52 = q.get("fiftyTwoWeekHigh")
        low52 = q.get("fiftyTwoWeekLow")
        pe = q.get("trailingPE")
        market_cap = q.get("marketCap")
        name = q.get("shortName", sym)

        trend = "📈 Tăng" if change > 0 else ("📉 Giảm" if change < 0 else "➡️ Đi ngang")

        cap_str = ""
        if market_cap:
            cap_b = market_cap / 1e9
            cap_str = f"${cap_b:.2f}B"

        return {
            "success": True,
            "ticker": sym,
            "name": name,
            "price": price,
            "change": round(change, 4),
            "change_pct": round(change_pct, 2),
            "volume": volume,
            "high_52w": high52,
            "low_52w": low52,
            "pe_ratio": round(pe, 2) if pe else None,
            "market_cap": market_cap,
            "trend": trend,
            "summary": (
                f"{name} ({sym}): {price:,.2f} ({change:+.2f}, {change_pct:+.2f}%)\n"
                f"  Volume: {volume:,} | 52w: {low52:.2f} – {high52:.2f}"
                + (f" | P/E: {pe:.2f}" if pe else "")
                + (f" | Market Cap: {cap_str}" if cap_str else "")
            ),
        }
    except (KeyError, IndexError, TypeError) as exc:
        return {"success": False, "error": f"Lỗi parse dữ liệu Yahoo Finance: {exc}"}


def analyze_stock(ticker: str, period: str = "3mo") -> dict:
    """Phân tích kỹ thuật cổ phiếu: RSI, MA20, MA50, tín hiệu.

    Args:
        ticker: Mã cổ phiếu (ví dụ: 'AAPL', 'VIC.VN').
        period: Khoảng thời gian ('1mo', '3mo', '6mo', '1y').
    """
    sym = ticker.upper().strip()
    interval_map = {"1mo": "1d", "3mo": "1d", "6mo": "1d", "1y": "1wk"}
    yf_interval = interval_map.get(period, "1d")

    data = _http_get(
        f"{YF_BASE}/{urllib.parse.quote(sym)}?period1=0&period2=9999999999"
        f"&interval={yf_interval}&range={period}",
        timeout=12,
    )
    if not data:
        return {"success": False, "error": f"Không kết nối được Yahoo Finance cho '{sym}'."}

    try:
        chart = data["chart"]["result"][0]
        closes_raw = chart["indicators"]["quote"][0]["close"]
        closes = [c for c in closes_raw if c is not None]
        if len(closes) < 10:
            return {"success": False, "error": "Không đủ dữ liệu lịch sử để phân tích."}

        current_price = closes[-1]
        ma20 = _sma(closes, 20)
        ma50 = _sma(closes, 50)
        rsi_val = _rsi(closes)

        signals = []
        if rsi_val < 30:
            signals.append("🟢 RSI quá bán — cân nhắc mua")
        elif rsi_val > 70:
            signals.append("🔴 RSI quá mua — cân nhắc chốt lời")

        if ma20 and current_price > ma20:
            signals.append("🟢 Giá trên MA20 — xu hướng ngắn hạn tích cực")
        elif ma20:
            signals.append("🔴 Giá dưới MA20 — xu hướng ngắn hạn tiêu cực")

        if ma50 and ma20 and ma20 > ma50:
            signals.append("🟢 Golden Cross — tín hiệu xu hướng tăng dài hạn")
        elif ma50 and ma20 and ma20 < ma50:
            signals.append("🔴 Death Cross — xu hướng giảm dài hạn")

        summary_lines = [
            f"📊 Phân tích kỹ thuật {sym} ({period}):",
            f"  Giá hiện tại: {current_price:,.2f}",
        ]
        if ma20:
            summary_lines.append(f"  MA20: {ma20:,.2f}")
        if ma50:
            summary_lines.append(f"  MA50: {ma50:,.2f}")
        summary_lines.append(f"  RSI(14): {rsi_val}")
        if signals:
            summary_lines.append("  Tín hiệu:")
            summary_lines.extend(f"    {s}" for s in signals)
        else:
            summary_lines.append("  Không có tín hiệu rõ ràng.")

        return {
            "success": True,
            "ticker": sym,
            "period": period,
            "current_price": current_price,
            "ma20": ma20,
            "ma50": ma50,
            "rsi": rsi_val,
            "signals": signals,
            "summary": "\n".join(summary_lines),
        }
    except (KeyError, IndexError, TypeError) as exc:
        return {"success": False, "error": f"Lỗi parse dữ liệu: {exc}"}


def compare_assets(tickers: list[str] | str) -> dict:
    """So sánh hiệu suất nhiều tài sản (cổ phiếu hoặc crypto) trong 30 ngày.

    Args:
        tickers: Danh sách mã tài sản, ví dụ ['AAPL', 'MSFT', 'NVDA']
                 hoặc chuỗi phân cách bằng dấu phẩy 'AAPL,MSFT,NVDA'.
    """
    if isinstance(tickers, str):
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    else:
        ticker_list = [t.strip().upper() for t in tickers]

    results = []
    for sym in ticker_list[:6]:  # Giới hạn 6 tài sản
        # Thử lấy từ Binance trước (crypto)
        is_crypto = any(
            sym.endswith(sfx) for sfx in ["USDT", "BTC", "ETH"]
        ) or len(sym) <= 5 and "." not in sym
        if is_crypto:
            csym = sym if sym.endswith("USDT") else sym + "USDT"
            t = _http_get(f"{BINANCE_BASE}/ticker/24hr?symbol={csym}")
            if t and "lastPrice" in t:
                pct = float(t["priceChangePercent"])
                results.append({"asset": sym, "type": "crypto", "change_24h_pct": pct, "price": float(t["lastPrice"])})
                continue

        # Fallback: Yahoo Finance (stocks)
        d = _http_get(
            f"{YF_QUOTE}?symbols={urllib.parse.quote(sym)}&fields=regularMarketPrice,regularMarketChangePercent",
            timeout=10,
        )
        if d:
            try:
                q = d["quoteResponse"]["result"][0]
                results.append({
                    "asset": sym,
                    "type": "stock",
                    "change_24h_pct": round(q.get("regularMarketChangePercent", 0), 2),
                    "price": q.get("regularMarketPrice", 0),
                })
            except (KeyError, IndexError):
                results.append({"asset": sym, "type": "unknown", "change_24h_pct": None, "price": None})

    # Sắp xếp theo hiệu suất giảm dần
    valid = sorted(
        [r for r in results if r["change_24h_pct"] is not None],
        key=lambda x: x["change_24h_pct"],
        reverse=True,
    )

    lines = ["📊 **So sánh hiệu suất 24h:**"]
    for r in valid:
        arrow = "▲" if r["change_24h_pct"] > 0 else "▼"
        price_str = f"${r['price']:,.4f}" if r["type"] == "crypto" else f"{r['price']:,.2f}"
        lines.append(f"  {'🥇' if valid.index(r) == 0 else '  '} {r['asset']}: {price_str} {arrow} {r['change_24h_pct']:+.2f}%")

    return {
        "success": True,
        "assets": valid,
        "summary": "\n".join(lines),
    }
