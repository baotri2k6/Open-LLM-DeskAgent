"""Evaluates agent performance across multiple dimensions."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.learning.performance_evaluator")


class PerformanceEvaluator:
    """Evaluates agent performance across multiple dimensions."""

    def __init__(self) -> None:
        self.metrics = {"success_count": 0, "failure_count": 0}

    def record_metrics(self, success: bool) -> None:
        if success:
            self.metrics["success_count"] += 1
        else:
            self.metrics["failure_count"] += 1

    def get_performance_ratio(self) -> float:
        total = self.metrics["success_count"] + self.metrics["failure_count"]
        if total == 0:
            return 1.0
        return self.metrics["success_count"] / total


# Global singleton
performance_evaluator = PerformanceEvaluator()
