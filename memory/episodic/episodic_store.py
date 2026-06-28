"""Stores episodic memories — conversations and events."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from config.config import WRITABLE_ROOT

logger = logging.getLogger("ai-companion.memory.episodic")


class EpisodicStore:
    """Stores episodic memories and conversational session records."""

    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or WRITABLE_ROOT / "data" / "episodic_memories.json"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.episodes: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.file_path.exists() and self.file_path.stat().st_size > 0:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.episodes = json.load(f)
            except Exception as e:
                logger.error("Failed to load episodic memories: %s", e)

    def _save(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.episodes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save episodic memories: %s", e)

    def record_episode(self, summary: str, sentiment: str = "neutral") -> None:
        self.episodes.append({
            "summary": summary,
            "sentiment": sentiment,
            "timestamp": time.time()
        })
        self._save()


# Global singleton
episodic_store = EpisodicStore()
