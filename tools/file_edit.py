"""Precise file editing tools for coding agents."""

from __future__ import annotations

from pathlib import Path


def _resolve_path(path: str) -> Path:
    if not path or not path.strip():
        raise ValueError("path is required")
    return Path(path).expanduser().resolve()


def str_replace_file(path: str, old_str: str, new_str: str) -> dict:
    """Replace exactly one occurrence of old_str in path with new_str."""
    try:
        if old_str == "":
            return {"success": False, "error": "old_str must not be empty"}

        p = _resolve_path(path)
        if not p.exists():
            return {"success": False, "error": f"File does not exist: {path}"}
        if not p.is_file():
            return {"success": False, "error": f"Path is not a file: {path}"}

        content = p.read_text(encoding="utf-8", errors="replace")
        occurrences = content.count(old_str)
        if occurrences != 1:
            return {
                "success": False,
                "error": (
                    f"old_str must appear exactly once in {path}; "
                    f"found {occurrences} occurrences. File was not modified."
                ),
                "occurrences": occurrences,
            }

        updated = content.replace(old_str, new_str, 1)
        p.write_text(updated, encoding="utf-8")
        return {
            "success": True,
            "message": f"Replaced 1 occurrence in {path}",
            "path": str(p),
            "bytes_before": len(content.encode("utf-8")),
            "bytes_after": len(updated.encode("utf-8")),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def create_file(path: str, content: str) -> dict:
    """Create a new file, failing if it already exists."""
    try:
        p = _resolve_path(path)
        if p.exists():
            return {"success": False, "error": f"File already exists: {path}"}

        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "message": f"Created file {path}",
            "path": str(p),
            "bytes_written": len(content.encode("utf-8")),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
