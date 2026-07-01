"""Embedding providers for local memory stores.

The memory layer must keep working offline. If the optional HuggingFace
integration or local model is unavailable, use a deterministic hash embedding
so Chroma can still store and retrieve memories without network access.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from pathlib import Path
from typing import Iterable

from config.config import PROJECT_ROOT

logger = logging.getLogger("ai-companion.memory.embeddings")


class HashEmbeddingFunction:
    """Small deterministic embedding function compatible with ChromaDB."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def __call__(self, input: Iterable[str]) -> list[list[float]]:
        return [self._embed(str(text)) for text in input]

    def embed_documents(self, texts: Iterable[str] | None = None, **kwargs) -> list[list[float]]:
        values = texts if texts is not None else kwargs.get("input", [])
        return [self._embed(str(text)) for text in values]

    def embed_query(self, text: str | None = None, **kwargs) -> list[float]:
        value = text if text is not None else kwargs.get("input", "")
        if isinstance(value, (list, tuple)):
            return [self._embed(str(item)) for item in value]
        return self._embed(str(value))

    def name(self) -> str:
        return "deskagent-hash-embedding"

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[\w']+", text.lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector


class HuggingFaceChromaEmbeddingFunction:
    """Adapter from LangChain HuggingFaceEmbeddings to ChromaDB's callable API."""

    def __init__(self, model_path: Path) -> None:
        from langchain_huggingface import HuggingFaceEmbeddings

        self._embeddings = HuggingFaceEmbeddings(
            model_name=str(model_path),
            model_kwargs={"device": "cpu"},
        )

    def __call__(self, input: Iterable[str]) -> list[list[float]]:
        return self._embeddings.embed_documents([str(text) for text in input])

    def embed_documents(self, texts: Iterable[str] | None = None, **kwargs) -> list[list[float]]:
        values = texts if texts is not None else kwargs.get("input", [])
        return self._embeddings.embed_documents([str(text) for text in values])

    def embed_query(self, text: str | None = None, **kwargs) -> list[float]:
        value = text if text is not None else kwargs.get("input", "")
        if isinstance(value, (list, tuple)):
            return self._embeddings.embed_documents([str(item) for item in value])
        return self._embeddings.embed_query(str(value))

    def name(self) -> str:
        return "deskagent-local-huggingface"


def get_default_embedding_function():
    local_model_path = PROJECT_ROOT / "models" / "embeddings" / "all-MiniLM-L6-v2"
    if local_model_path.exists():
        try:
            return HuggingFaceChromaEmbeddingFunction(local_model_path)
        except Exception as exc:
            logger.warning("Local HuggingFace embedding unavailable, using hash fallback: %s", exc)

    return HashEmbeddingFunction()


class EmbeddingService:
    def __init__(self) -> None:
        self.embeddings = get_default_embedding_function()
