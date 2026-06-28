"""Processing pipeline for input/output flow."""

from __future__ import annotations

import logging
from typing import Any, Callable, List

logger = logging.getLogger("ai-companion.runtime.pipeline")


class Pipeline:
    """Sequentially executes registered processing stages on inputs."""

    def __init__(self) -> None:
        self._stages: List[Callable[[Any], Any]] = []

    def add_stage(self, stage_fn: Callable[[Any], Any]) -> None:
        """Add a stage function to the pipeline."""
        self._stages.append(stage_fn)

    def process(self, input_data: Any) -> Any:
        """Run input through all registered pipeline stages sequentially."""
        current = input_data
        for i, stage in enumerate(self._stages):
            try:
                current = stage(current)
            except Exception as e:
                logger.error("Pipeline stage %d failed: %s", i, e)
        return current
