"""Retrieval Engine — unified interface to retrieve relevant memories."""

from __future__ import annotations

import logging
from typing import Any, List
from memory.semantic.long_term import long_term_store

logger = logging.getLogger("ai-companion.memory.retrieval")


class RetrievalEngine:
    """Unified retrieval interface across memory types."""

    def __init__(self) -> None:
        self._long_term = long_term_store

    def retrieve_relevant(self, query: str, limit: int = 5) -> List[str]:
        """Query long-term store and return relevant snippets."""
        if not query.strip():
            return []
        
        results = self._long_term.search_facts(query, n_results=limit)
        snippets = []
        for fact in results:
            snippets.append(fact["text"])
        return snippets


# Global singleton
retrieval_engine = RetrievalEngine()
