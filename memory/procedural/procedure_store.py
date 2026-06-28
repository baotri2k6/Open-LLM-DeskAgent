"""Stores procedural memories — how to do things."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from config.config import WRITABLE_ROOT

logger = logging.getLogger("ai-companion.memory.procedural")


class ProcedureStore:
    """Stores recipes, procedural skills, and how-to steps."""

    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or WRITABLE_ROOT / "data" / "procedural_memories.json"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.procedures: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        if self.file_path.exists() and self.file_path.stat().st_size > 0:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.procedures = json.load(f)
            except Exception as e:
                logger.error("Failed to load procedural memories: %s", e)

    def _save(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.procedures, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save procedural memories: %s", e)

    def register_procedure(self, name: str, steps: list[str]) -> None:
        self.procedures[name] = steps
        self._save()

    def get_procedure(self, name: str) -> list[str] | None:
        return self.procedures.get(name)


# Global singleton
procedure_store = ProcedureStore()
