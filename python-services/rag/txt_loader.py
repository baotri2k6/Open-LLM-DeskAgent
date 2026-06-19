"""Plain-text loader (.txt, .md)."""

from __future__ import annotations

from pathlib import Path

from core.logger import get_logger

logger = get_logger("ai-companion.rag.loaders.txt")

SUPPORTED_EXT = {".txt", ".md", ".markdown", ".log"}


def load(path: str | Path) -> str:
    p = Path(path)
    # Thử utf-8 trước, fallback latin-1 (đọc được hầu hết text)
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Không đọc được {p} với encoding phổ biến")
