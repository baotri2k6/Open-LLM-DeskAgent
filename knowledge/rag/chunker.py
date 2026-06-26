"""Document chunker — chia tài liệu thành các đoạn nhỏ để embed."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class Chunk:
    text: str
    doc_id: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.doc_id}__chunk_{self.chunk_index}"


def _split_paragraphs(text: str) -> list[str]:
    """Tách text thành đoạn theo dòng trống."""
    blocks = re.split(r"\n{2,}", text.strip())
    return [b.strip() for b in blocks if b.strip()]


def _sliding_window(text: str, chunk_size: int = 400, overlap: int = 80) -> Iterator[str]:
    """Sliding window theo từ."""
    words = text.split()
    if len(words) <= chunk_size:
        yield text
        return
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        yield " ".join(words[start:end])
        if end == len(words):
            break
        start += chunk_size - overlap


def chunk_text(
    text: str,
    doc_id: str,
    chunk_size: int = 400,
    overlap: int = 80,
    metadata: dict | None = None,
) -> list[Chunk]:
    """Chia text thành list Chunk."""
    metadata = metadata or {}
    paragraphs = _split_paragraphs(text)
    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_len = 0

    def flush(buf: list[str]) -> None:
        combined = " ".join(buf)
        for piece in _sliding_window(combined, chunk_size, overlap):
            if piece.strip():
                chunks.append(
                    Chunk(
                        text=piece.strip(),
                        doc_id=doc_id,
                        chunk_index=len(chunks),
                        metadata=metadata.copy(),
                    )
                )

    for para in paragraphs:
        words = len(para.split())
        if buffer_len + words > chunk_size * 1.5:
            if buffer:
                flush(buffer)
                buffer = []
                buffer_len = 0
        buffer.append(para)
        buffer_len += words

    if buffer:
        flush(buffer)

    # đảm bảo index liên tục
    for i, chunk in enumerate(chunks):
        chunk.chunk_index = i

    return chunks