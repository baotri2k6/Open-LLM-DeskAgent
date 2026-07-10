"""Updates beliefs from new evidence and interactions."""

from __future__ import annotations

import logging
from belief.belief_store import belief_store

logger = logging.getLogger("ai-companion.belief.updater")


class BeliefUpdater:
    """Updates and manages life cycles of companion beliefs based on fresh evidence."""

    def __init__(self) -> None:
        pass

    def register_evidence(self, key: str, value: str, confidence: float = 0.5, source: str = "observation") -> None:
        """Register or reinforce a belief. Increases confidence if value matches, updates otherwise."""
        existing = belief_store.get_belief(key)
        if existing:
            if existing.value == value:
                # Reinforce belief confidence
                new_conf = min(1.0, existing.confidence + (confidence * 0.2))
                belief_store.set_belief(key, value, new_conf, source)
                logger.info("BeliefUpdater: Reinforced belief '%s' to confidence %.2f", key, new_conf)
            else:
                # Contradicting belief: lower confidence first
                new_conf = existing.confidence - (confidence * 0.5)
                if new_conf <= 0.2:
                    # Overwrite belief since confidence is too low
                    belief_store.set_belief(key, value, confidence, source)
                    logger.info("BeliefUpdater: Overwrote contradicted belief '%s' with new value '%s'", key, value)
                else:
                    existing.confidence = new_conf
                    belief_store._save()
                    logger.info("BeliefUpdater: Contradicted belief '%s' confidence decayed to %.2f", key, new_conf)
        else:
            belief_store.set_belief(key, value, confidence, source)

    def decay_all(self, amount: float = 0.02) -> None:
        """Slightly decay confidence of all stored beliefs to represent memory fade over time."""
        for belief in belief_store.list_all_beliefs():
            belief_store.decay_confidence(belief.key, amount)


# Global singleton
belief_updater = BeliefUpdater()
