"""Embedding helper interface for memory module."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ai-companion.memory.embeddings")


def get_default_embedding_function() -> Any:
    """Return default embedding function, fallback to default chroma if needed."""
    try:
        from chromadb.utils import embedding_functions  # type: ignore
        try:
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        except Exception:
            return embedding_functions.DefaultEmbeddingFunction()
    except Exception as e:
        logger.warning("Failed to initialize embedding function: %s", e)
        return None
