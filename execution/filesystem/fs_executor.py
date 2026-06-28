"""File system read/write/move operations."""

from __future__ import annotations

import os
import shutil
import logging

logger = logging.getLogger("ai-companion.execution.fs")


class FilesystemExecutor:
    """Safe filesystem operations wrapper."""

    def __init__(self) -> None:
        pass

    def read_file(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: str, content: str) -> bool:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    def delete_file(self, path: str) -> bool:
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


# Global singleton
fs_executor = FilesystemExecutor()
