"""Web search tool — dùng DuckDuckGo HTML (không cần API key)."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser


class _DDGParser(HTMLParser):
    """Parse kết quả tìm kiếm DuckDuckGo HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict] = []
        self._current: dict = {}
        self._capture_title_tag = None
        self._capture_snippet_tag = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attr_dict = dict(attrs)
        cls = attr_dict.get("class", "")
        if "result__title" in cls:
            self._capture_title_tag = tag
        if "result__snippet" in cls:
            self._capture_snippet_tag = tag
        if tag == "a" and "result__url" in cls:
            self._current["url"] = attr_dict.get("href", "")

    def handle_endtag(self, tag: str) -> None:
        if self._capture_title_tag == tag:
            self._capture_title_tag = None
        if self._capture_snippet_tag == tag:
            self._capture_snippet_tag = None
            if self._current.get("title") or self._current.get("snippet"):
                self.results.append(dict(self._current))
                self._current = {}

    def handle_data(self, data: str) -> None:
        if self._capture_title_tag is not None:
            self._current.setdefault("title", "")
            self._current["title"] += data
        if self._capture_snippet_tag is not None:
            self._current.setdefault("snippet", "")
            self._current["snippet"] += data


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Tìm kiếm DuckDuckGo, trả về list {title, snippet, url}."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        parser = _DDGParser()
        parser.feed(html)
        return parser.results[:max_results]
    except Exception as exc:
        return [{"error": str(exc)}]