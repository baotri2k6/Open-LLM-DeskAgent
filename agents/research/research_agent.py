"""ResearchAgent — gathers, reads, and synthesizes research context."""

from __future__ import annotations

import re
import inspect
from pathlib import Path
from typing import Any

from config.config import PROJECT_ROOT


class ResearchAgent:
    """A lightweight research agent that works with local files and optional web tools."""

    name = "research"
    capabilities = ["research_web", "literature_search", "synthesize_report", "read_sources"]

    async def execute_task(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        query = str(payload.get("query") or payload.get("task") or "").strip()
        sources = payload.get("sources") or payload.get("focus_files") or []

        if capability == "research_web":
            return await self._execute_web_research(query)
        if capability == "synthesize_report" and "snippets" in payload:
            return await self._execute_synthesize_report(list(payload.get("snippets") or []), query=query)
        if capability in {"read_sources", "literature_search"}:
            return self.read_sources(sources=sources, query=query)
        if capability == "synthesize_report":
            source_result = self.read_sources(sources=sources, query=query)
            return self.synthesize(query=query, notes=source_result.get("notes", []))
        return {"success": False, "error": f"Unsupported research capability: {capability}"}

    async def handle_message(self, text: str, context: dict | None = None) -> dict[str, Any]:
        context = context or {}
        return self.synthesize(
            query=text,
            notes=self.read_sources(context.get("focus_files", []), text).get("notes", []),
        )

    def __init__(self, llm_service: Any | None = None) -> None:
        self.llm_service = llm_service

    def read_sources(self, sources: list[str] | None = None, query: str = "") -> dict[str, Any]:
        notes: list[dict[str, str]] = []
        for source in sources or []:
            path = self._resolve_source(source)
            if not path or not path.exists() or not path.is_file():
                notes.append({"source": str(source), "status": "missing", "excerpt": ""})
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                notes.append({"source": str(source), "status": "error", "excerpt": str(exc)})
                continue

            notes.append({
                "source": str(path.relative_to(PROJECT_ROOT)) if path.is_relative_to(PROJECT_ROOT) else str(path),
                "status": "ok",
                "excerpt": self._best_excerpt(text, query),
            })

        return {"success": True, "query": query, "notes": notes}

    def research_web(self, query: str) -> dict[str, Any]:
        """Use the existing web_search tool when available; otherwise return a plan."""
        if not query:
            return {"success": False, "error": "Missing query"}
        try:
            from tools.web_search import search_web

            result = search_web(query)
            return {"success": True, "query": query, "result": result}
        except Exception as exc:
            return {
                "success": False,
                "query": query,
                "error": str(exc),
                "fallback_plan": [
                    f"Clarify research question: {query}",
                    "Collect primary sources or local docs",
                    "Extract claims, tradeoffs, and open questions",
                    "Synthesize into a short decision-ready report",
                ],
            }

    def synthesize(self, query: str, notes: list[dict[str, str]] | None = None) -> dict[str, Any]:
        notes = notes or []
        ok_notes = [note for note in notes if note.get("status") == "ok" and note.get("excerpt")]
        bullets = []
        for note in ok_notes[:5]:
            excerpt = re.sub(r"\s+", " ", note["excerpt"]).strip()
            bullets.append(f"{note['source']}: {excerpt[:280]}")

        if not bullets:
            bullets = ["No usable source excerpts were provided; gather sources before final conclusions."]

        return {
            "success": True,
            "query": query,
            "report": "\n".join(bullets),
            "summary": "Research synthesis ready from available context.",
            "findings": bullets,
            "source_count": len(ok_notes),
        }

    async def _llm_report(self, prompt: str) -> str:
        if not self.llm_service or not hasattr(self.llm_service, "chat"):
            return ""
        result = self.llm_service.chat(prompt)
        if inspect.isawaitable(result):
            result = await result
        return str(result)

    async def _execute_web_research(self, query: str) -> dict[str, Any]:
        try:
            from tools import browser_control

            raw = browser_control.search_google(query)
            if inspect.isawaitable(raw):
                raw = await raw
        except Exception as exc:
            raw = f"search failed: {exc}"

        report = await self._llm_report(f"Research query: {query}\nRaw data:\n{raw}")
        if not report:
            report = str(raw)
        return {"success": True, "query": query, "raw_data": raw, "report": report}

    async def _execute_synthesize_report(self, snippets: list[str], query: str = "") -> dict[str, Any]:
        raw = "\n".join(str(s) for s in snippets)
        report = await self._llm_report(f"Synthesize research report for: {query}\nSnippets:\n{raw}")
        if not report:
            report = raw or "No snippets provided."
        return {"success": True, "query": query, "raw_data": snippets, "report": report}

    def _resolve_source(self, source: str) -> Path | None:
        if not source:
            return None
        path = Path(source)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        try:
            resolved = path.resolve()
            if PROJECT_ROOT in resolved.parents or resolved == PROJECT_ROOT:
                return resolved
        except Exception:
            return None
        return None

    def _best_excerpt(self, text: str, query: str, max_chars: int = 900) -> str:
        text = text.strip()
        if not text:
            return ""
        terms = [term.lower() for term in re.findall(r"[\wÀ-ỹ]+", query) if len(term) > 2]
        if not terms:
            return text[:max_chars]

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        scored = []
        for line in lines:
            lower = line.lower()
            score = sum(1 for term in terms if term in lower)
            if score:
                scored.append((score, line))
        if scored:
            scored.sort(key=lambda item: item[0], reverse=True)
            return "\n".join(line for _, line in scored[:5])[:max_chars]
        return text[:max_chars]


research_agent = ResearchAgent()
