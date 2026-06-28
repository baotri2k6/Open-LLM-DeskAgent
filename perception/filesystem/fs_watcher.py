"""Watches filesystem for file change events."""

from __future__ import annotations

from pathlib import Path

from config.config import PROJECT_ROOT


class FilesystemWatcher:
    """Lightweight polling watcher for project files."""

    def __init__(self) -> None:
        self._snapshot: dict[str, float] = {}

    def scan(self, root: str | Path | None = None, max_files: int = 500) -> dict:
        base = Path(root or PROJECT_ROOT).resolve()
        current: dict[str, float] = {}
        changed: list[str] = []

        if not base.exists():
            return {"root": str(base), "changed": [], "files_seen": 0}

        for path in base.rglob("*"):
            if len(current) >= max_files:
                break
            if any(part in {".git", "node_modules", "__pycache__", "dist", "build"} for part in path.parts):
                continue
            if path.is_file():
                key = str(path)
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    continue
                current[key] = mtime
                if self._snapshot and self._snapshot.get(key) != mtime:
                    changed.append(key)

        self._snapshot = current
        return {"root": str(base), "changed": changed, "files_seen": len(current)}


filesystem_watcher = FilesystemWatcher()
