"""Evaluates task success and quality."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.learning.task_evaluator")


class TaskEvaluator:
    """Evaluates task success and quality."""

    def __init__(self) -> None:
        pass

    def evaluate(self, task_id: str, success: bool, feedback: str) -> dict:
        """Generate evaluation metrics for a task."""
        score = 1.0 if success else 0.0
        if "excellent" in feedback.lower():
            score = 1.2
        elif "poor" in feedback.lower():
            score = 0.2
            
        return {
            "task_id": task_id,
            "success": success,
            "quality_score": score,
            "feedback_length": len(feedback)
        }


# Global singleton
task_evaluator = TaskEvaluator()
