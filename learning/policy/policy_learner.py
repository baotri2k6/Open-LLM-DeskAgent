"""Learns behavioral policies from reward signals."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.learning.policy")


class PolicyLearner:
    """Learns behavioral policies from reward signals."""

    def __init__(self) -> None:
        self.policy_weights: dict[str, float] = {}

    def update_policy(self, state_action: str, reward: float) -> None:
        """Simple Q-learning update emulation for policy adjustment."""
        current_weight = self.policy_weights.get(state_action, 0.0)
        # Learning rate of 0.1
        self.policy_weights[state_action] = current_weight + 0.1 * (reward - current_weight)
        logger.info("PolicyLearner: Updated %s weight to %.2f", state_action, self.policy_weights[state_action])


# Global singleton
policy_learner = PolicyLearner()
