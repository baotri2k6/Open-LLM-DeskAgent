"""RAG retriever — import tài liệu và truy vấn ngữ cảnh liên quan."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from core.logger import get_logger
from rag.chunker import chunk_text
from rag.document_loader import load_document
from rag.vector_store import get_vector_store

logger = get_logger("ai-companion.rag.retriever")


def _doc_id(path: str) -> str:
    """Tạo doc_id ổn định từ path."""
    return hashlib.md5(str(Path(path).resolve()).encode()).hexdigest()[:12]


class RAGRetriever:
    def __init__(self, collection: str = "documents") -> None:
        self._store = get_vector_store(collection)
        self._collection = collection

    # ── Import ────────────────────────────────────────────────────────────────

    def import_document(
        self,
        path: str,
        chunk_size: int = 400,
        overlap: int = 80,
    ) -> dict[str, Any]:
        """
        Load + chunk + embed một tài liệu.
        Trả về: {success, doc_id, chunk_count, format, char_count}
        """
        result = load_document(path)
        if not result["success"]:
            return result

        doc_id = _doc_id(path)
        filename = Path(path).name
        metadata = {
            "filename": filename,
            "format": result.get("format", ""),
            "path": str(Path(path).resolve()),
        }

        chunks = chunk_text(
            text=result["text"],
            doc_id=doc_id,
            chunk_size=chunk_size,
            overlap=overlap,
            metadata=metadata,
        )
        if not chunks:
            return {"success": False, "error": "Tài liệu rỗng hoặc không đọc được text."}

        self._store.add_chunks(chunks)
        logger.info("Imported '%s' → %d chunks (doc_id=%s)", filename, len(chunks), doc_id)

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": filename,
            "chunk_count": len(chunks),
            "format": result.get("format"),
            "char_count": result.get("char_count", 0),
        }

    # ── Retrieve ──────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        n_results: int = 4,
        doc_id: str | None = None,
    ) -> list[dict]:
        """Tìm chunks liên quan nhất theo query."""
        return self._store.query(query, n_results=n_results, doc_id=doc_id)

    def build_context(self, query: str, n_results: int = 4, doc_id: str | None = None) -> str:
        """Trả về context string để đưa vào LLM prompt."""
        chunks = self.retrieve(query, n_results=n_results, doc_id=doc_id)
        if not chunks:
            return ""
        pieces = [f"[{c.get('filename', c.get('doc_id', ''))}]\n{c['text']}" for c in chunks]
        return "\n\n---\n\n".join(pieces)

    # ── Management ────────────────────────────────────────────────────────────

    def list_documents(self) -> list[str]:
        return self._store.list_docs()

    def delete_document(self, doc_id: str) -> None:
        self._store.delete_doc(doc_id)
        logger.info("Deleted doc '%s'", doc_id)


# singleton — một instance mỗi collection
_retrievers: dict[str, "RAGRetriever"] = {}


def get_retriever(collection: str = "documents") -> "RAGRetriever":
    if collection not in _retrievers:
        _retrievers[collection] = RAGRetriever(collection)
    return _retrievers[collection]