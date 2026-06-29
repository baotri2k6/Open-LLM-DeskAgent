"""Queries beliefs to inform companion responses."""

from __future__ import annotations

from typing import List, Optional
from belief.belief_store import belief_store, Belief


class BeliefQuery:
    """Queries beliefs to filter, search and retrieve user traits and preferences."""

    def __init__(self) -> None:
        pass

    def query_by_prefix(self, prefix: str) -> List[Belief]:
        """Query all beliefs whose key starts with the given prefix."""
        all_beliefs = belief_store.list_all_beliefs()
        return [b for b in all_beliefs if b.key.startswith(prefix)]

    def query_high_confidence(self, min_confidence: float = 0.7) -> List[Belief]:
        """Query all beliefs that have confidence equal to or higher than threshold."""
        all_beliefs = belief_store.list_all_beliefs()
        return [b for b in all_beliefs if b.confidence >= min_confidence]

    def get_value(self, key: str, default: str | None = None) -> str | None:
        """Get value of a specific belief directly."""
        belief = belief_store.get_belief(key)
        return belief.value if belief else default


# Global singleton
belief_query = BeliefQuery()
