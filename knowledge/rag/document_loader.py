"""Document loader — dispatch theo extension."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from runtime.logger import get_logger
from rag import docx_loader, pdf_loader, txt_loader

logger = get_logger("ai-companion.knowledge.knowledge.knowledge.knowledge.rag.document_loader")

_FORMAT_BY_EXT: dict[str, tuple[str, Callable[[Path], str]]] = {
    ".txt": ("txt", txt_loader.load),
    ".md": ("md", txt_loader.load),
    ".markdown": ("md", txt_loader.load),
    ".log": ("txt", txt_loader.load),
    ".docx": ("docx", docx_loader.load),
    ".pdf": ("pdf", pdf_loader.load),
}


def _detect_format(path: Path) -> tuple[str, Callable[[Path], str]] | None:
    ext = path.suffix.lower()
    return _FORMAT_BY_EXT.get(ext)


def load_document(path: str) -> dict[str, Any]:
    """Đọc tài liệu và trả dict:
        {success, text, format, char_count, error?}
    """
    p = Path(path)
    if not p.exists():
        return {"success": False, "error": f"File không tồn tại: {path}"}
    if not p.is_file():
        return {"success": False, "error": f"Không phải file: {path}"}

    detected = _detect_format(p)
    if not detected:
        return {
            "success": False,
            "error": (
                f"Định dạng '{p.suffix}' chưa hỗ trợ. "
                "Hỗ trợ: .txt, .md, .docx, .pdf"
            ),
        }

    fmt, loader = detected
    try:
        text = loader(p)
    except Exception as exc:
        logger.warning("Load %s failed: %s", p, exc)
        return {"success": False, "error": f"Không đọc được file: {exc}"}

    if not text or not text.strip():
        return {
            "success": False,
            "error": "File rỗng hoặc không trích xuất được text (có thể là ảnh scan).",
        }

    return {
        "success": True,
        "text": text.strip(),
        "format": fmt,
        "char_count": len(text.strip()),
    }
