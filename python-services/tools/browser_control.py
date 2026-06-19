"""Browser control — mở URL trong trình duyệt mặc định."""

from __future__ import annotations

import webbrowser


def open_url(url: str) -> dict:
    """Mở URL trong trình duyệt mặc định của hệ thống."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        webbrowser.open(url)
        return {"success": True, "url": url}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def search_google(query: str) -> dict:
    """Mở Google tìm kiếm với query cho trước."""
    import urllib.parse
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    return open_url(url)


def search_coccoc(query: str) -> dict:
    """Mở Cốc Cốc tìm kiếm với query cho trước."""
    import urllib.parse
    url = f"https://coccoc.com/search?q={urllib.parse.quote_plus(query)}"
    return open_url(url)