"""Top-level runtime orchestrator — boots all subsystems."""

from __future__ import annotations

import logging
from typing import Any
from runtime.services.service_registry import service_registry

logger = logging.getLogger("ai-companion.runtime.manager")


class RuntimeManager:
    """Top-level runtime orchestrator — boots all subsystems."""

    def __init__(self) -> None:
        self._booted = False

    def boot(self) -> None:
        """Boot all background subsystems."""
        if self._booted:
            return
        logger.info("RuntimeManager: Booting background subsystems...")
        
        # Register base backend status
        service_registry.register("backend", lambda: {"status": "running"})
        
        self._booted = True
        logger.info("RuntimeManager: All subsystems booted successfully ✓")

    def shutdown(self) -> None:
        """Gracefully shutdown all subsystems."""
        if not self._booted:
            return
        logger.info("RuntimeManager: Shutting down subsystems...")
        self._booted = False
        logger.info("RuntimeManager: Subsystems shut down ✓")


# Global singleton
runtime_manager = RuntimeManager()
