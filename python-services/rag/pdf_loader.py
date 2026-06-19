"""PDF loader (PyMuPDF / fitz)."""

from __future__ import annotations

from pathlib import Path

from core.logger import get_logger

logger = get_logger("ai-companion.rag.loaders.pdf")


def load(path: str | Path) -> str:
    try:
        import fitz  # type: ignore  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "Thiếu PyMuPDF. Cài: pip install PyMuPDF"
        ) from exc

    doc = fitz.open(str(Path(path)))
    parts: list[str] = []
    try:
        for page_index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                parts.append(f"\n## Trang {page_index}\n{text}")
    finally:
        doc.close()
    return "\n".join(parts).strip()
