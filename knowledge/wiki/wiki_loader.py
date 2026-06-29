"""Loads and indexes wiki knowledge into the knowledge base."""

from __future__ import annotations

import logging
import urllib.request
import urllib.parse
import json

logger = logging.getLogger("ai-companion.knowledge.wiki")


class WikiLoader:
    """Fetches articles from Wikipedia and returns clean indexable text blocks."""

    def __init__(self) -> None:
        pass

    def fetch_summary(self, topic: str) -> str | None:
        """Fetch summary of a topic from Wikipedia API."""
        encoded_topic = urllib.parse.quote(topic)
        url = f"https://vi.wikipedia.org/api/rest_v1/page/summary/{encoded_topic}"
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'DeskAgent/1.0 (baotri2k6@gmail.com) Python-urllib/3'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                extract = data.get("extract")
                if extract:
                    logger.info("WikiLoader: Successfully fetched summary for '%s'", topic)
                    return extract
        except Exception as e:
            logger.warning("WikiLoader: Failed to fetch Wikipedia page summary for '%s': %s", topic, e)
        return None


# Global singleton
wiki_loader = WikiLoader()
