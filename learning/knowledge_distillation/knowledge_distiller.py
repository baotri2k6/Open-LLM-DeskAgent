"""KnowledgeDistiller — đúc kết tri thức quan trọng từ ExperienceStore thành facts ngắn gọn."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from learning.experience.experience_store import experience_store

logger = logging.getLogger("ai-companion.learning.distillation")


try:
    from config.config import WRITABLE_ROOT
    _DISTILLED_PATH = WRITABLE_ROOT / "data" / "distilled_knowledge.json"
except Exception:
    _DISTILLED_PATH = Path("data") / "distilled_knowledge.json"


class KnowledgeDistiller:
    """Đúc kết tri thức từ ExperienceStore thành các quy tắc ngắn gọn."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DISTILLED_PATH

    def distill_experiences(self) -> None:
        """Đúc kết các trải nghiệm thất bại và thành công thành bài học kinh nghiệm."""
        failures = experience_store.get_failures()
        successes = [e for e in experience_store.get_recent_experiences(limit=20) if e.is_successful]

        distilled: List[str] = []

        # 1. Đúc kết từ các thất bại để tránh lặp lại sai lầm
        for e in failures[-5:]:
            lesson = e.lessons_learned.strip()
            if lesson:
                fact = f"Tránh lỗi trong nhiệm vụ '{e.goal_desc}': {lesson}"
                if fact not in distilled:
                    distilled.append(fact)

        # 2. Đúc kết từ thành công để củng cố cách làm đúng
        for e in successes[-5:]:
            lesson = e.lessons_learned.strip()
            if lesson:
                fact = f"Đã thành công trong '{e.goal_desc}' nhờ: {lesson}"
                if fact not in distilled:
                    distilled.append(fact)

        # Giới hạn số lượng bài học truyền vào prompt để tiết kiệm token
        distilled = distilled[-5:]

        logger.info("KnowledgeDistiller: Distilled %d facts from experiences", len(distilled))
        self._save(distilled)

    def get_distilled_facts_for_prompt(self) -> List[str]:
        """Lấy các bài học kinh nghiệm đã đúc kết để đưa vào system prompt."""
        return self._load()

    def describe_for_prompt(self) -> str:
        """Trả về chuỗi bài học kinh nghiệm định dạng cho system prompt."""
        facts = self.get_distilled_facts_for_prompt()
        if not facts:
            return ""
        formatted = "\n".join(f"- {f}" for f in facts)
        return f"[Distilled Lessons]\n{formatted}"

    def _save(self, facts: List[str]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(facts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save distilled knowledge: %s", e)

    def _load(self) -> List[str]:
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error("Failed to load distilled knowledge: %s", e)
        return []


# Global singleton
knowledge_distiller = KnowledgeDistiller()
