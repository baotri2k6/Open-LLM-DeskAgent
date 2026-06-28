"""ChromaDB persistent store implementation for memory module."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List
from config.config import WRITABLE_ROOT
from memory.embeddings.embeddings import get_default_embedding_function

logger = logging.getLogger("ai-companion.memory.vectorstore.chroma")


class ChromaMemoryStore:
    """ChromaDB store for companion memories, independent of RAG."""

    def __init__(self, collection_name: str = "companion_memories") -> None:
        try:
            import chromadb  # type: ignore
        except ImportError:
            raise RuntimeError("chromadb is not installed. Run pip install chromadb")

        persist_dir = WRITABLE_ROOT / "data" / "memory_vectorstore" / collection_name
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._embed_fn = get_default_embedding_function()

        self._col = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def add_memories(self, ids: List[str], documents: List[str], metadatas: List[dict]) -> None:
        """Add memories/facts to Chroma collection."""
        if not ids:
            return
        self._col.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def query_memories(self, text: str, n_results: int = 5) -> List[dict]:
        """Query memories from collection."""
        count = self._col.count() or 1
        res = self._col.query(
            query_texts=[text],
            n_results=min(n_results, count)
        )
        if not res or not res.get("ids") or not res["ids"][0]:
            return []

        output = []
        for i, doc_id in enumerate(res["ids"][0]):
            output.append({
                "id": doc_id,
                "text": res["documents"][0][i],
                "metadata": res["metadatas"][0][i] if res.get("metadatas") else {},
                "score": res["distances"][0][i] if res.get("distances") else 0.0
            })
        return output


# Alias for compatibility
ChromaStore = ChromaMemoryStore
