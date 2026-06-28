"""Builds and updates the knowledge graph from new information."""

from __future__ import annotations

import logging
import re
from typing import List, Tuple
from knowledge.graph.knowledge_graph import KnowledgeGraph, knowledge_graph

logger = logging.getLogger("ai-companion.knowledge.graph_builder")


class GraphBuilder:
    """Analyzes text facts to extract semantic triplets and populate the KnowledgeGraph."""

    def __init__(self, graph: KnowledgeGraph | None = None) -> None:
        self.graph = graph or knowledge_graph

    def build_from_fact(self, fact_text: str) -> List[Tuple[str, str, str]]:
        """Parse fact_text and add detected triplets to the graph."""
        triplets: List[Tuple[str, str, str]] = []
        text_lower = fact_text.lower()
        
        if "thích" in text_lower or "love" in text_lower:
            m = re.search(r"(?:cậu ấy|user|người dùng|tôi)\s+thích\s+([^.,?!]+)", fact_text, re.IGNORECASE)
            if m:
                obj = m.group(1).strip()
                self.graph.add_relation("User", obj, "LIKES")
                triplets.append(("User", "LIKES", obj))
                
        if "làm việc tại" in text_lower or "works at" in text_lower:
            m = re.search(r"(?:cậu ấy|user|người dùng|tôi)\s+làm việc tại\s+([^.,?!]+)", fact_text, re.IGNORECASE)
            if m:
                obj = m.group(1).strip()
                self.graph.add_relation("User", obj, "WORKS_AT")
                triplets.append(("User", "WORKS_AT", obj))
                
        logger.info("GraphBuilder: Extracted %d triplets from fact: '%s'", len(triplets), fact_text)
        return triplets


# Global singleton
graph_builder = GraphBuilder()
