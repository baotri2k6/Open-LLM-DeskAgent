"""Common helper utilities for safe file operations."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("ai-companion.tools.file_utils")


def get_dir_size_bytes(directory: str | Path) -> int:
    """Calculate the total size of all files inside a directory."""
    total_size = 0
    try:
        path = Path(directory)
        if path.exists() and path.is_dir():
            for root, _, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
    except Exception as e:
        logger.warning("Failed to calculate directory size: %s", e)
    return total_size


def safe_delete_file(filepath: str | Path) -> bool:
    """Safely delete file if it exists."""
    try:
        path = Path(filepath)
        if path.exists() and path.is_file():
            path.unlink()
            return True
    except Exception as e:
        logger.warning("Failed to safely delete file %s: %s", filepath, e)
    return False
