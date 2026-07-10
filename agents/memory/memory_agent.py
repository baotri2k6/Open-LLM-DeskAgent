"""Memory agent wrapping the JSON memory service."""

from __future__ import annotations

import logging
from memory.memory_service import MemoryService
from learning.knowledge.knowledge_extractor import knowledge_extractor

logger = logging.getLogger("ai-companion.agents.memory")


class MemoryAgent:
    """Agent that governs memory processing, filtering, and storage decisions."""

    def __init__(self, service: MemoryService | None = None) -> None:
        self.service = service or MemoryService()

    def remember(self, text: str) -> dict:
        """Evaluate if the conversation text contains worth-remembering facts and store them."""
        text_clean = text.strip()
        if not text_clean:
            return {"success": False, "reason": "Empty content"}
            
        # Auto extract facts
        extracted = knowledge_extractor.extract_from_text(text_clean)
        
        # Save to memory service
        result = self.service.remember(text_clean)
        result["extracted_facts"] = list(extracted.keys())
        
        logger.info("MemoryAgent: Evaluated and saved memory. Extracted %d facts.", len(extracted))
        return result

    def recall(self, query: str = "") -> list[dict]:
        """Query memory service and rank/filter results by relevance."""
        logger.info("MemoryAgent: Recalling context for query: '%s'", query)
        raw_results = self.service.recall(query)
        return raw_results

    def profile(self) -> dict:
        """Retrieve compiled user profile and preferences summary."""
        return self.service.get_profile()
