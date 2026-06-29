"""Manages context window and compression."""

from __future__ import annotations

import logging
from typing import List
from runtime.context.context_packet import ContextPacket

logger = logging.getLogger("ai-companion.cognition.context")


class ContextManager:
    """Manages the context window history and compression logic."""

    def __init__(self, max_history: int = 15) -> None:
        self.max_history = max_history
        self._history: List[ContextPacket] = []

    def add_packet(self, packet: ContextPacket) -> None:
        """Add a ContextPacket to the history."""
        self._history.append(packet)
        if len(self._history) > self.max_history:
            self._history.pop(0)

    def get_history(self) -> List[ContextPacket]:
        """Get the current context packet history."""
        return self._history

    def get_aggregated_context(self) -> Dict[str, Any]:
        """Aggregate history packets to construct a unified view of recent activities."""
        if not self._history:
            return {
                "active_window": "Unknown",
                "total_idle_seconds": 0.0,
                "recent_activities": [],
                "recent_user_messages": []
            }
            
        latest = self._history[-1]
        
        # Aggregate active windows and user messages
        activities = []
        user_messages = []
        total_idle = 0.0
        
        for p in self._history:
            if p.activity and p.activity not in activities:
                activities.append(p.activity)
            if p.user_message:
                user_messages.append(p.user_message)
            total_idle += p.idle_seconds
            
        knowledge_triplets = []
        try:
            from knowledge.graph.knowledge_graph import knowledge_graph
            knowledge_triplets = knowledge_graph.get_all_triplets()
        except Exception as e:
            logger.warning("ContextManager failed to query knowledge graph: %s", e)

        return {
            "active_window": latest.active_window or "Unknown",
            "total_idle_seconds": round(total_idle, 2),
            "recent_activities": activities,
            "recent_user_messages": user_messages,
            "knowledge_graph": knowledge_triplets
        }

    def clear(self) -> None:
        """Clear context packet history."""
        self._history.clear()


# Global singleton
context_manager = ContextManager()
