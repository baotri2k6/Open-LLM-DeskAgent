"""Long-term Memory Store — persist facts to ChromaDB."""

from __future__ import annotations

import logging
import json
import time
import difflib
from typing import Any, List, Optional
from config.config import WRITABLE_ROOT
from memory.vectorstore.chroma_store import ChromaMemoryStore

logger = logging.getLogger("ai-companion.memory.long_term")


class LongTermMemoryStore:
    """Stores and queries semantic facts using ChromaMemoryStore."""

    def __init__(self) -> None:
        self._fallback_path = WRITABLE_ROOT / "data" / "long_term_facts.json"
        self._fallback_facts: list[dict] = self._load_fallback()
        try:
            self._vector_store = ChromaMemoryStore("companion_memories")
            self._available = True
        except Exception as e:
            logger.warning("ChromaMemoryStore not available: %s", e)
            self._available = False

    def add_fact(self, text: str, category: str = "note", metadata: Optional[dict] = None) -> bool:
        cleaned = text.strip()
        if not cleaned:
            return False
        stored_in_vector = False
        try:
            if self._available:
                doc_id = str(abs(hash(cleaned)) % 1000000)
                self._vector_store.add_memories(
                    ids=[doc_id],
                    documents=[cleaned],
                    metadatas=[{**(metadata or {}), "category": category}]
                )
                stored_in_vector = True
        except Exception as e:
            logger.error("Failed to add long-term memory: %s", e)
            self._available = False

        self._add_fallback_fact(cleaned, category, metadata or {})
        return True if not stored_in_vector else True

    def search_facts(self, query: str, n_results: int = 5) -> List[dict]:
        if not query.strip():
            return []
        try:
            if self._available:
                results = self._vector_store.query_memories(query, n_results=n_results)
                recalled = []
                for item in results:
                    recalled.append({
                        "text": item["text"],
                        "category": item.get("metadata", {}).get("category", "note"),
                        "score": item.get("score", 0.0)
                    })
                if recalled:
                    return recalled
        except Exception as e:
            logger.warning("Long term query failed: %s", e)
            self._available = False
        return self._search_fallback(query, n_results)

    def _add_fallback_fact(self, text: str, category: str, metadata: dict) -> None:
        doc_id = str(abs(hash(text)) % 1000000)
        for fact in self._fallback_facts:
            if fact.get("id") == doc_id:
                return
        self._fallback_facts.append({
            "id": doc_id,
            "text": text,
            "category": category,
            "metadata": metadata,
            "created_at": time.time(),
        })
        self._save_fallback()

    def _search_fallback(self, query: str, n_results: int) -> list[dict]:
        q = query.lower().strip()
        scored = []
        for fact in self._fallback_facts:
            text = str(fact.get("text", ""))
            lower = text.lower()
            overlap = len(set(q.split()) & set(lower.split()))
            fuzzy = difflib.SequenceMatcher(None, q, lower).ratio()
            score = overlap + fuzzy
            if score > 0.1:
                scored.append((score, fact))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "text": fact.get("text", ""),
                "category": fact.get("category", "note"),
                "score": float(score),
            }
            for score, fact in scored[:n_results]
        ]

    def _load_fallback(self) -> list[dict]:
        try:
            if self._fallback_path.exists() and self._fallback_path.stat().st_size > 0:
                with self._fallback_path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    def _save_fallback(self) -> None:
        try:
            self._fallback_path.parent.mkdir(parents=True, exist_ok=True)
            with self._fallback_path.open("w", encoding="utf-8") as handle:
                json.dump(self._fallback_facts, handle, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("Failed to save fallback long-term memory: %s", exc)


# Global singleton
long_term_store = LongTermMemoryStore()
