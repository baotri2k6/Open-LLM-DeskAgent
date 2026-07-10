"""KnowledgeDistiller — distills durable facts from accumulated experiences."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from config.config import WRITABLE_ROOT
from learning.experience.experience_store import Experience, experience_store


@dataclass
class DistilledFact:
    """A compact fact suitable for system prompt injection."""

    key: str
    text: str
    category: str = "general"
    confidence: float = 0.5
    evidence_count: int = 1
    updated_at: float = field(default_factory=time.time)


class KnowledgeDistiller:
    """Turns repeated task experiences into short reusable knowledge facts."""

    PATTERNS: list[tuple[str, str, str]] = [
        (r"permission denied|access is denied|phân quyền|quyền", "system.permission", "When a task hits permission errors, ask for approval or use the approved permission path before retrying."),
        (r"pytest|unit test|test fail|tests? failed", "workflow.tests", "For code changes, run the focused test first, then broaden to related suites."),
        (r"network|offline|connection|urlopen|internet", "system.network", "Network-dependent tools must degrade gracefully and provide an offline fallback."),
        (r"chromadb|embedding|sentence-transformers|vector", "memory.vectorstore", "Vector memory can fail when embeddings are unavailable; keep JSON or in-memory fallback active."),
        (r"mcp|uvx|cache", "tools.mcp", "MCP tools may fail from external cache permissions; report degraded status instead of blocking the app."),
        (r"config|api key|secret|\.env", "security.config", "Never commit local API keys; prefer environment overrides and ignored config files."),
    ]

    def __init__(self, facts_path: Path | None = None) -> None:
        self._path = facts_path or WRITABLE_ROOT / "data" / "distilled_knowledge.json"
        self._facts: dict[str, DistilledFact] = self._load()

    def distill_from_experiences(self, experiences: Iterable[Experience] | None = None) -> list[DistilledFact]:
        """Distill facts from experiences and persist the updated fact set."""
        experiences = list(experiences) if experiences is not None else experience_store.get_recent_experiences(50)
        changed: list[DistilledFact] = []

        for exp in experiences:
            text = f"{exp.goal_desc}\n{exp.lessons_learned}".lower()
            metadata = exp.metadata or {}
            for regex, key, fact_text in self.PATTERNS:
                if re.search(regex, text, re.IGNORECASE):
                    changed.append(self._upsert_fact(key, fact_text, category=key.split(".")[0], success=exp.is_successful))

            tool = metadata.get("tool") or metadata.get("tool_name")
            if tool:
                tool_key = f"tool.{tool}"
                tool_text = f"Tool '{tool}' has appeared in prior work; consider its past outcomes before using it again."
                changed.append(self._upsert_fact(tool_key, tool_text, category="tool", success=exp.is_successful))

        if changed:
            self.save()
        return changed

    def get_facts(self, limit: int = 8, min_confidence: float = 0.35) -> list[DistilledFact]:
        facts = [fact for fact in self._facts.values() if fact.confidence >= min_confidence]
        facts.sort(key=lambda f: (f.confidence, f.evidence_count, f.updated_at), reverse=True)
        return facts[:limit]

    def get_prompt_facts(self, limit: int = 6) -> list[str]:
        return [
            f"- {fact.text} (confidence {fact.confidence:.2f}, evidence {fact.evidence_count})"
            for fact in self.get_facts(limit=limit)
        ]

    def describe_for_prompt(self, limit: int = 6) -> str:
        lines = self.get_prompt_facts(limit=limit)
        if not lines:
            return ""
        return "[Distilled Knowledge]\n" + "\n".join(lines)

    def _upsert_fact(self, key: str, text: str, category: str, success: bool) -> DistilledFact:
        existing = self._facts.get(key)
        confidence_delta = 0.08 if success else 0.12
        if existing:
            existing.evidence_count += 1
            existing.confidence = round(min(1.0, existing.confidence + confidence_delta), 3)
            existing.updated_at = time.time()
            return existing

        fact = DistilledFact(
            key=key,
            text=text,
            category=category,
            confidence=0.55 if success else 0.65,
        )
        self._facts[key] = fact
        return fact

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump([asdict(fact) for fact in self._facts.values()], handle, ensure_ascii=False, indent=2)

    def _load(self) -> dict[str, DistilledFact]:
        try:
            if self._path.exists() and self._path.stat().st_size > 0:
                with self._path.open("r", encoding="utf-8") as handle:
                    raw = json.load(handle)
                facts = {}
                for item in raw if isinstance(raw, list) else []:
                    fact = DistilledFact(
                        key=item["key"],
                        text=item["text"],
                        category=item.get("category", "general"),
                        confidence=float(item.get("confidence", 0.5)),
                        evidence_count=int(item.get("evidence_count", 1)),
                        updated_at=float(item.get("updated_at", time.time())),
                    )
                    facts[fact.key] = fact
                return facts
        except Exception:
            pass
        return {}


knowledge_distiller = KnowledgeDistiller()
