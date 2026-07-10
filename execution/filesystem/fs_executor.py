"""File system read/write/move operations."""

from __future__ import annotations

import logging
from pathlib import Path

from config.config import PROJECT_ROOT, WRITABLE_ROOT
from execution.approval.approval_registry import PermissionManager

logger = logging.getLogger("ai-companion.execution.fs")


class FilesystemExecutor:
    """Safe filesystem operations wrapper."""

    def __init__(self) -> None:
        self._roots = [PROJECT_ROOT.resolve(), WRITABLE_ROOT.resolve()]

    def _resolve_allowed_path(self, path: str) -> Path:
        p = Path(path).expanduser().resolve()
        if not any(root == p or root in p.parents for root in self._roots):
            raise PermissionError(f"Path is outside allowed workspace roots: {path}")
        return p

    def read_file(self, path: str) -> str:
        p = self._resolve_allowed_path(path)
        with p.open("r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: str, content: str) -> bool:
        if PermissionManager.requires_approval("write_to_file", {"path": path}):
            raise PermissionError(f"Writing requires approval: {path}")
        p = self._resolve_allowed_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            f.write(content)
        return True

    def delete_file(self, path: str) -> bool:
        if PermissionManager.requires_approval("delete_file", {"path": path}):
            raise PermissionError(f"Deleting requires approval: {path}")
        p = self._resolve_allowed_path(path)
        if p.exists():
            p.unlink()
            return True
        return False


# Global singleton
fs_executor = FilesystemExecutor()
