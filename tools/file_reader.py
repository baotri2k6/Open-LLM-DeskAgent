"""File reader — đọc PDF, DOCX, TXT."""

from __future__ import annotations

from pathlib import Path


def read_file(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"success": False, "error": f"File khong ton tai: {path}"}
    suffix = p.suffix.lower()
    try:
        if suffix == ".txt" or suffix in (".md", ".log", ".csv", ".json"):
            text = p.read_text(encoding="utf-8", errors="replace")
            return {"success": True, "text": text[:8000], "truncated": len(text) > 8000}

        if suffix == ".pdf":
            import fitz  # PyMuPDF
            doc = fitz.open(str(p))
            pages = [page.get_text() for page in doc]
            text = "\n".join(pages)
            return {"success": True, "text": text[:8000], "pages": len(pages), "truncated": len(text) > 8000}

        if suffix == ".docx":
            from docx import Document
            doc = Document(str(p))
            text = "\n".join(para.text for para in doc.paragraphs)
            return {"success": True, "text": text[:8000], "truncated": len(text) > 8000}

        return {"success": False, "error": f"Dinh dang '{suffix}' chua duoc ho tro."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}