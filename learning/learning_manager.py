"""Orchestrates the learning pipeline."""

from __future__ import annotations

import logging
from typing import Any
from learning.policy.policy_learner import PolicyLearner
from learning.evaluation.task_evaluator import TaskEvaluator

logger = logging.getLogger("ai-companion.learning.manager")


class LearningManager:
    """Orchestrates the learning pipeline."""

    def __init__(self) -> None:
        self.learner = PolicyLearner()
        self.evaluator = TaskEvaluator()

    def process_task_outcome(self, task_id: str, success: bool, feedback: str) -> None:
        """Process feedback and update learning policy."""
        logger.info("LearningManager: Processing task outcome for %s (success=%s)", task_id, success)
        reward = 1.0 if success else -1.0
        self.learner.update_policy(task_id, reward)
        evaluation = self.evaluator.evaluate(task_id, success, feedback)
        logger.info("LearningManager: Task evaluation: %s", evaluation)

        # Wire KnowledgeExtractor to extract new beliefs/rules from task outcome/feedback
        try:
            from learning.knowledge.knowledge_extractor import knowledge_extractor
            extracted = knowledge_extractor.extract_from_text(feedback)
            if extracted:
                logger.info("LearningManager: Extracted knowledge facts: %s", extracted)
        except Exception as e:
            logger.warning("LearningManager failed to run KnowledgeExtractor: %s", e)

        try:
            from learning.experience.experience_store import experience_store
            from learning.distillation.knowledge_distiller import knowledge_distiller
            from learning.patterns.pattern_learner import pattern_learner

            exp = experience_store.record_experience(
                goal_id=task_id,
                goal_desc=f"Task outcome: {task_id}",
                is_successful=success,
                lessons_learned=feedback,
                metadata={"activity": "coding" if "code" in feedback.lower() else "task", "tool": task_id},
            )
            knowledge_distiller.distill_from_experiences([exp])
            pattern_learner.observe_experience(exp)
        except Exception as e:
            logger.warning("LearningManager failed to run distillation/pattern learning: %s", e)


# Global singleton
learning_manager = LearningManager()
