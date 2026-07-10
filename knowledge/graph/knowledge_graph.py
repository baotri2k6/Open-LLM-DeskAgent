"""Knowledge graph — entity-relation store for semantic facts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set

logger = logging.getLogger("ai-companion.knowledge.graph")


@dataclass
class Entity:
    name: str
    type: str = "concept"  # e.g., person, tech, preference, hobby
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class Relation:
    source: str
    target: str
    type: str  # e.g., LIKES, WORKS_ON, HAS_STATUS


class KnowledgeGraph:
    """In-memory entity-relation graph store for structuring semantic facts."""

    def __init__(self) -> None:
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []

    def add_entity(self, name: str, type: str = "concept", attrs: Dict[str, str] | None = None) -> Entity:
        """Add a new node (entity) to the graph."""
        if name not in self.entities:
            self.entities[name] = Entity(name=name, type=type, attributes=attrs or {})
        else:
            if attrs:
                self.entities[name].attributes.update(attrs)
        return self.entities[name]

    def add_relation(self, source: str, target: str, rel_type: str) -> None:
        """Add a directed edge (relation) between two entities."""
        self.add_entity(source)
        self.add_entity(target)
        
        # Check if relation already exists
        for r in self.relations:
            if r.source == source and r.target == target and r.type == rel_type:
                return
                
        self.relations.append(Relation(source=source, target=target, type=rel_type))
        logger.info("KnowledgeGraph: Added relation %s -[%s]-> %s", source, rel_type, target)

    def query_connections(self, entity_name: str) -> List[dict]:
        """Find all relations connected to the given entity."""
        results = []
        for r in self.relations:
            if r.source == entity_name:
                results.append({"target": r.target, "type": r.type, "direction": "outgoing"})
            elif r.target == entity_name:
                results.append({"source": r.source, "type": r.type, "direction": "incoming"})
        return results

    def get_all_triplets(self) -> List[tuple[str, str, str]]:
        """Return graph as a list of (source, relation, target) triplets."""
        return [(r.source, r.type, r.target) for r in self.relations]


# Global singleton
knowledge_graph = KnowledgeGraph()
