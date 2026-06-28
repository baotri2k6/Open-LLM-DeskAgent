"""Handles execution failures and recovery strategies."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.execution.recovery")


class RecoveryHandler:
    """Handles execution failures and recovery strategies."""

    def __init__(self) -> None:
        pass

    def handle_failure(self, error_msg: str, task_context: str) -> str:
        """Suggests a recovery action depending on the error message."""
        logger.warning("RecoveryHandler: Encountered error: %s", error_msg)
        if "permission denied" in error_msg.lower():
            return "ASK_FOR_APPROVAL"
        if "file not found" in error_msg.lower():
            return "SEARCH_WORKSPACE"
        return "RETRY"


# Global singleton
recovery_handler = RecoveryHandler()
