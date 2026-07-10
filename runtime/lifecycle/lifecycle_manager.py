"""LifecycleManager — orchestrates toàn bộ startup và shutdown.

Đảm bảo các modules được khởi tạo đúng thứ tự và
cleanup sạch sẽ khi shutdown.

Startup order:
  1. Config      — load cấu hình
  2. EventBus    — messaging backbone
  3. StateStore  — companion state machine
  4. Memory      — persistent + working memory
  5. Persona     — emotion, mood, relationship
  6. Motivation  — needs, drives, boredom
  7. Speech      — STT + TTS engines
  8. LifeLoop    — autonomous background loop
  9. API Server  — HTTP + WebSocket endpoints
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("ai-companion.runtime.lifecycle")


@dataclass
class StartupStatus:
    """Trạng thái khởi động của từng module."""
    module:   str
    success:  bool
    duration: float = 0.0
    error:    str   = ""


class LifecycleManager:
    """Orchestrates startup và shutdown của toàn bộ companion system.

    Được gọi từ api/server.py khi FastAPI startup event.
    """

    def __init__(self) -> None:
        self._startup_results: list[StartupStatus] = []
        self._started_at: Optional[float] = None
        self._is_ready: bool = False

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    @property
    def startup_duration(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    async def startup(self) -> bool:
        """Khởi động tất cả modules theo thứ tự.

        Returns:
            True nếu core modules (config, memory, persona) đều OK.
        """
        self._started_at = time.time()
        logger.info("=== Lifecycle: STARTUP BEGIN ===")

        # Module startup steps (tên, coroutine hoặc callable)
        steps = [
            ("Config",     self._init_config),
            ("EventBus",   self._init_eventbus),
            ("StateStore", self._init_state_store),
            ("Memory",     self._init_memory),
            ("Persona",    self._init_persona),
            ("Motivation", self._init_motivation),
            ("Agents",     self._init_agents),
            ("LifeLoop",   self._init_life_loop),
        ]

        critical_failed = False
        critical_modules = {"Config", "Memory", "Persona"}

        for name, fn in steps:
            t0 = time.time()
            try:
                if asyncio.iscoroutinefunction(fn):
                    await fn()
                else:
                    fn()
                duration = time.time() - t0
                self._startup_results.append(StartupStatus(name, True, duration))
                logger.info("  [OK] %-15s (%.2fs)", name, duration)
            except Exception as e:
                duration = time.time() - t0
                self._startup_results.append(StartupStatus(name, False, duration, str(e)))
                logger.error("  [FAIL] %-13s — %s", name, e)
                if name in critical_modules:
                    critical_failed = True

        total = time.time() - self._started_at
        self._is_ready = not critical_failed
        status = "READY" if self._is_ready else "DEGRADED"
        logger.info("=== Lifecycle: %s (%.2fs) ===", status, total)
        return self._is_ready

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("=== Lifecycle: SHUTDOWN BEGIN ===")
        try:
            from life.life_loop import life_loop
            life_loop.stop()
        except Exception as e:
            logger.warning("LifeLoop stop error: %s", e)

        try:
            from runtime.session.session_manager import session_manager
            session_manager.end_session("System shutdown")
        except Exception as e:
            logger.warning("Session end error: %s", e)

        logger.info("=== Lifecycle: SHUTDOWN COMPLETE ===")

    def get_startup_report(self) -> list[dict]:
        """Trả về report startup cho API /health."""
        return [
            {
                "module":   r.module,
                "success":  r.success,
                "duration": round(r.duration, 3),
                "error":    r.error,
            }
            for r in self._startup_results
        ]

    # ── Module initializers ────────────────────────────────────────────────

    def _init_config(self) -> None:
        from config.config import config  # noqa: F401

    def _init_eventbus(self) -> None:
        from runtime.eventbus.event_bus import event_bus  # noqa: F401

    def _init_state_store(self) -> None:
        from runtime.state.state_store import state_store  # noqa: F401

    def _init_memory(self) -> None:
        from memory.memory_manager import memory_manager
        memory_manager.get_profile()  # Trigger lazy init

    def _init_persona(self) -> None:
        from persona.emotion.emotion_engine import emotion_engine  # noqa: F401
        from persona.mood.mood_engine import mood_engine            # noqa: F401
        from persona.relationship.relationship_tracker import relationship_tracker  # noqa: F401

    def _init_motivation(self) -> None:
        from motivation.motivation_manager import motivation_manager  # noqa: F401

    def _init_agents(self) -> None:
        from agents.registry.agent_registry import agent_registry
        from agents.planner.planner_agent import PlannerAgent
        from agents.browser.browser_agent import BrowserAgent
        from agents.memory.memory_agent import MemoryAgent
        from agents.vision.vision_agent import VisionAgent
        from agents.desktop.desktop_agent import DesktopAgent
        from agents.research.research_agent import ResearchAgent
        
        # Instantiate agents
        planner = PlannerAgent()
        browser = BrowserAgent()
        memory = MemoryAgent()
        vision = VisionAgent()
        desktop = DesktopAgent()
        research = ResearchAgent()
        
        # Register capabilities
        agent_registry.register("planner", planner, ["classify_intent", "route_task"])
        agent_registry.register("browser", browser, ["web_search", "open_url"])
        agent_registry.register("memory", memory, ["remember", "recall"])
        agent_registry.register("vision", vision, ["screen_read", "describe_screen"])
        agent_registry.register("desktop", desktop, ["open_app", "execute_command"])
        agent_registry.register("research", research, ["research_web", "literature_search", "synthesize_report", "read_sources"])

    async def _init_life_loop(self) -> None:
        from life.life_loop import life_loop
        await life_loop.start_async()


# Global singleton
lifecycle_manager = LifecycleManager()
