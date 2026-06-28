"""Long-term Memory Store — persist facts to ChromaDB."""

from __future__ import annotations

import logging
from typing import Any, List, Optional
from memory.vectorstore.chroma_store import ChromaMemoryStore

logger = logging.getLogger("ai-companion.memory.long_term")


class LongTermMemoryStore:
    """Stores and queries semantic facts using ChromaMemoryStore."""

    def __init__(self) -> None:
        try:
            self._vector_store = ChromaMemoryStore("companion_memories")
            self._available = True
        except Exception as e:
            logger.warning("ChromaMemoryStore not available: %s", e)
            self._available = False

    def add_fact(self, text: str, category: str = "note", metadata: Optional[dict] = None) -> bool:
        if not self._available:
            return False
        try:
            doc_id = str(hash(text) % 1000000)
            self._vector_store.add_memories(
                ids=[doc_id],
                documents=[text.strip()],
                metadatas=[{**(metadata or {}), "category": category}]
            )
            return True
        except Exception as e:
            logger.error("Failed to add long-term memory: %s", e)
            return False

    def search_facts(self, query: str, n_results: int = 5) -> List[dict]:
        if not self._available or not query.strip():
            return []
        try:
            results = self._vector_store.query_memories(query, n_results=n_results)
            recalled = []
            for item in results:
                recalled.append({
                    "text": item["text"],
                    "category": item.get("metadata", {}).get("category", "note"),
                    "score": item.get("score", 0.0)
                })
            return recalled
        except Exception as e:
            logger.warning("Long term query failed: %s", e)
            return []


# Global singleton
long_term_store = LongTermMemoryStore()
