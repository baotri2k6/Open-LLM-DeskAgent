"""Domain ontology — structured vocabulary and concept hierarchy."""

from __future__ import annotations

import logging
from typing import Dict, List, Set

logger = logging.getLogger("ai-companion.knowledge.ontology")


class Ontology:
    """Maintains a semantic concept hierarchy (IS_A relations)."""

    def __init__(self) -> None:
        # concept -> parent concept
        self._hierarchy: Dict[str, str] = {}
        # Prepopulate default common desktop ontology
        self.add_class("python", "programming_language")
        self.add_class("typescript", "programming_language")
        self.add_class("chess", "game")
        self.add_class("vscode", "editor")

    def add_class(self, child_class: str, parent_class: str) -> None:
        """Add a subclass relation to the ontology hierarchy."""
        self._hierarchy[child_class.lower()] = parent_class.lower()
        logger.info("Ontology: Registered subclass relation: %s IS_A %s", child_class, parent_class)

    def is_subclass_of(self, child: str, parent: str) -> bool:
        """Check if child inherits from parent (recursive traversal)."""
        curr = child.lower()
        target = parent.lower()
        
        visited: Set[str] = set()
        while curr in self._hierarchy:
            if curr == target:
                return True
            if curr in visited:
                break  # Prevent infinite loops
            visited.add(curr)
            curr = self._hierarchy[curr]
            
        return curr == target

    def get_parent(self, concept: str) -> str | None:
        """Get direct parent class of a concept."""
        return self._hierarchy.get(concept.lower())


# Global singleton
ontology = Ontology()
