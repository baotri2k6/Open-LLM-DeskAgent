"""Vector store cho RAG.

Hai api:
  1. ChromaDB + sentence-transformers (ưu tiên, semantic search).
  2. In-memory fallback (TF-IDF-lite bằng difflib.SequenceMatcher) — chạy được
     khi thiếu package, đủ dùng cho vài chục chunks.

Cả hai đều cùng API:
    add_chunks(chunks: list[Chunk]) -> None
    query(text, n_results, doc_id=None) -> list[dict]   # {text, metadata, score}
    list_docs() -> list[str]
    delete_doc(doc_id) -> None
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, Protocol

from config.config import WRITABLE_ROOT
from runtime.logger import get_logger
from .chunker import Chunk

logger = get_logger("ai-companion.knowledge.rag.vector_store")


# ─── VectorStore protocol ──────────────────────────────────────────────────


class VectorStore(Protocol):
    def add_chunks(self, chunks: list[Chunk]) -> None: ...
    def query(
        self, text: str, n_results: int = 4, doc_id: str | None = None
    ) -> list[dict]: ...
    def list_docs(self) -> list[str]: ...
    def delete_doc(self, doc_id: str) -> None: ...


# ─── Backend 1: ChromaDB ──────────────────────────────────────────────────


class ChromaStore:
    """ChromaDB api với sentence-transformers embeddings.

    Lưu persistent tại PROJECT_ROOT/data/vectorstore/<collection>.
    """

    def __init__(self, collection: str) -> None:
        try:
            import chromadb  # type: ignore
            from chromadb.utils import embedding_functions  # type: ignore
        except ImportError:
            raise RuntimeError("chromadb chưa cài. pip install chromadb")

        persist_dir = WRITABLE_ROOT / "data" / "vectorstore" / collection
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(persist_dir))

        # Ưu tiên sentence-transformers; fallback default embedding của chroma
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            model_name = "all-MiniLM-L6-v2"
            self._embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name
            )
            # Warm-up: tải model ngay để lần query đầu không bị block
            SentenceTransformer(model_name)
        except ImportError:
            logger.warning("sentence-transformers chưa có → dùng default embedding")
            self._embed_fn = embedding_functions.DefaultEmbeddingFunction()

        self._col = self._client.get_or_create_collection(
            name=collection,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        self._col.upsert(
            ids=[c.id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[
                {**c.metadata, "doc_id": c.doc_id, "chunk_index": c.chunk_index}
                for c in chunks
            ],
        )

    def query(
        self, text: str, n_results: int = 4, doc_id: str | None = None
    ) -> list[dict]:
        kwargs: dict = {"query_texts": [text], "n_results": min(n_results, self._col.count() or 1)}
        if doc_id:
            kwargs["where"] = {"doc_id": doc_id}

        res = self._col.query(**kwargs)
        out: list[dict] = []
        # res = {"ids": [[...]], "documents": [[...]], "metadatas": [[...]], "distances": [[...]]}
        if not res or not res.get("ids") or not res["ids"][0]:
            return []
        for i, doc_id_or_chunk in enumerate(res["ids"][0]):
            text_ = res["documents"][0][i]
            meta = res["metadatas"][0][i] if res.get("metadatas") else {}
            dist = res["distances"][0][i] if res.get("distances") else 0.0
            out.append(
                {
                    "id": doc_id_or_chunk,
                    "text": text_,
                    "metadata": meta,
                    "filename": meta.get("filename", ""),
                    "doc_id": meta.get("doc_id", ""),
                    "score": max(0.0, 1.0 - float(dist)),  # cosine distance → similarity
                }
            )
        return out

    def list_docs(self) -> list[str]:
        # Lấy distinct doc_id từ metadata
        try:
            data = self._col.get(include=["metadatas"])
        except Exception:
            return []
        seen: set[str] = set()
        for m in data.get("metadatas") or []:
            if isinstance(m, dict) and m.get("doc_id"):
                seen.add(m["doc_id"])
        return sorted(seen)

    def delete_doc(self, doc_id: str) -> None:
        self._col.delete(where={"doc_id": doc_id})


# ─── Backend 2: In-memory fallback ────────────────────────────────────────


_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _WORD_RE.findall(text)]


class InMemoryStore:
    """Backend đơn giản, dùng TF-IDF + cosine similarity.

    Phù hợp demo / fallback khi chưa cài chromadb + sentence-transformers.
    """

    def __init__(self) -> None:
        # chunk_id → {text, doc_id, chunk_index, metadata, vector}
        self._chunks: dict[str, dict] = {}
        self._df: Counter = Counter()  # document frequency cho IDF
        self._dirty = True

    def _rebuild_index(self) -> None:
        # Tính IDF + vector chuẩn hoá cho mỗi chunk
        n = max(1, len(self._chunks))
        for ch in self._chunks.values():
            tf = Counter(_tokenize(ch["text"]))
            vec: dict[str, float] = {}
            for term, freq in tf.items():
                idf = math.log((1 + n) / (1 + self._df.get(term, 0))) + 1.0
                vec[term] = (1 + math.log(freq)) * idf
            # L2 normalize
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            ch["vector"] = {k: v / norm for k, v in vec.items()}
        self._dirty = False

    def add_chunks(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._chunks[c.id] = {
                "text": c.text,
                "doc_id": c.doc_id,
                "chunk_index": c.chunk_index,
                "metadata": c.metadata,
                "vector": {},
            }
            for term in set(_tokenize(c.text)):
                self._df[term] += 1
        self._dirty = True

    def _query_vector(self, text: str) -> dict[str, float]:
        n = max(1, len(self._chunks))
        tf = Counter(_tokenize(text))
        vec: dict[str, float] = {}
        for term, freq in tf.items():
            idf = math.log((1 + n) / (1 + self._df.get(term, 0))) + 1.0
            vec[term] = (1 + math.log(freq)) * idf
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {k: v / norm for k, v in vec.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        # duyệt dict nhỏ hơn
        if len(a) > len(b):
            a, b = b, a
        return sum(v * b.get(k, 0.0) for k, v in a.items())

    def query(
        self, text: str, n_results: int = 4, doc_id: str | None = None
    ) -> list[dict]:
        if not self._chunks:
            return []
        if self._dirty:
            self._rebuild_index()
        qvec = self._query_vector(text)
        pool: Iterable[dict] = self._chunks.values()
        if doc_id:
            pool = (c for c in self._chunks.values() if c["doc_id"] == doc_id)
        scored = [
            (self._cosine(qvec, c["vector"]), c) for c in pool
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[dict] = []
        for score, ch in scored[:n_results]:
            if score <= 0:
                continue
            out.append(
                {
                    "id": ch.get("chunk_index"),  # không có id đầy đủ ở đây
                    "text": ch["text"],
                    "metadata": ch["metadata"],
                    "filename": ch["metadata"].get("filename", ""),
                    "doc_id": ch["doc_id"],
                    "score": float(score),
                }
            )
        return out

    def list_docs(self) -> list[str]:
        return sorted({c["doc_id"] for c in self._chunks.values()})

    def delete_doc(self, doc_id: str) -> None:
        to_remove = [cid for cid, c in self._chunks.items() if c["doc_id"] == doc_id]
        for cid in to_remove:
            del self._chunks[cid]
        # Tính lại DF
        self._df = Counter()
        for ch in self._chunks.values():
            for term in set(_tokenize(ch["text"])):
                self._df[term] += 1
        self._dirty = True


# ─── Singleton factory ────────────────────────────────────────────────────


_stores: dict[str, VectorStore] = {}


def get_vector_store(collection: str = "documents") -> VectorStore:
    """Trả singleton cho từng collection. Thử ChromaDB trước, fallback in-memory."""
    if collection in _stores:
        return _stores[collection]

    api: VectorStore
    try:
        api = ChromaStore(collection)
        logger.info("VectorStore[%s] → ChromaDB", collection)
    except Exception as exc:
        logger.warning("ChromaDB unavailable (%s) → in-memory fallback", exc)
        api = InMemoryStore()

    _stores[collection] = api
    return api
