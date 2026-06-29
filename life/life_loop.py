"""Life Loop — main autonomous async loop: Observe → Feel → Decide → Act."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger("ai-companion.life")


class LifeLoop:
    """
    The autonomous life loop that makes the companion proactively alive.

    Runs as a background asyncio task inside the Python server.
    Cycle: Observe → Feel → Decide → Act → Sleep → Repeat

    Integration: Started from api/server.py on startup via asyncio.create_task().
    """

    def __init__(self, ws_clients: Optional[set] = None) -> None:
        self._ws_clients  = ws_clients or set()
        self._running     = False
        self._task: Optional[asyncio.Task] = None
        self._decay_task: Optional[asyncio.Task] = None

    def start(self, ws_clients: Optional[set] = None) -> None:
        """Start the life loop as an asyncio background task."""
        if ws_clients:
            self._ws_clients = ws_clients
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self._run())
            self._decay_task = loop.create_task(self._run_periodic_decay())
            logger.info("LifeLoop: Started ✓")
        except RuntimeError:
            logger.warning("LifeLoop: No running event loop — will start on next await")

    def stop(self) -> None:
        """Stop the life loop."""
        self._running = False
        if self._task:
            self._task.cancel()
        if self._decay_task:
            self._decay_task.cancel()
        logger.info("LifeLoop: Stopped")

    async def start_async(self, ws_clients: Optional[set] = None) -> None:
        """Start the life loop from an async context."""
        if ws_clients:
            self._ws_clients = ws_clients
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        self._decay_task = asyncio.create_task(self._run_periodic_decay())
        logger.info("LifeLoop: Started (async) ✓")

    # ── Main loop ──────────────────────────────────────────────────────────

    async def _run(self) -> None:
        """Main coroutine — loops until stopped."""
        # Lazy imports to avoid circular dependencies at startup
        from life.observe.observer import life_observer
        from life.decide.decision_engine import decision_engine
        from life.act.proactive_messenger import proactive_messenger
        from persona.mood.mood_engine import mood_engine
        from persona.emotion.emotion_engine import emotion_engine

        # Wire WebSocket clients to messenger
        proactive_messenger.register_ws_clients(self._ws_clients)

        # Configure decision engine from config
        try:
            from config.config import config
            interval = float(config.get("life.proactive_interval_seconds", 600))
            decision_engine.configure(interval)
        except Exception:
            pass

        logger.info("LifeLoop: Entering main loop")

        while self._running:
            try:
                # ── Observe ────────────────────────────────────────────────
                mood_state = mood_engine.state
                context = life_observer.observe(
                    mood    = mood_state.mood,
                    emotion = emotion_engine.emotion,
                    energy  = mood_state.energy,
                )

                # Log the observed activity to the ActivityTimeline
                try:
                    from world.timeline.activity_timeline import activity_timeline
                    activity_timeline.log_event(context.last_user_activity)
                except Exception as tl_err:
                    logger.warning("LifeLoop: Failed to log observed activity to timeline: %s", tl_err)

                # ── Evolve Persona ─────────────────────────────────────────
                from persona.persona_manager import persona_manager
                persona_manager.evolve_personality()

                # ── Feel — update emotional and mood states ────────────────
                from life.feel.feel_engine import feel_engine
                feel_engine.feel(context)

                # ── Think — internal monologue ────────────────────────────
                from life.think.thinker import thinker
                thought_res = thinker.think(context)

                # ── Decide ─────────────────────────────────────────────────
                decision = decision_engine.decide(context)
                
                # Áp dụng silence policy từ Thinker
                if thought_res.get("stay_silent"):
                    decision.should_act = False

                # ── Act ────────────────────────────────────────────────────
                action_taken = False
                if decision.should_act:
                    action_taken = await proactive_messenger.send(
                        action_type  = decision.action_type,
                        message_hint = decision.message_hint,
                    )

                # ── Reflect ────────────────────────────────────────────────
                from life.reflect.reflect_engine import reflect_engine
                reflect_engine.reflect_cycle(context, decision, action_taken)

                # ── Belief Decay ───────────────────────────────────────────
                try:
                    from belief.belief_updater import belief_updater
                    belief_updater.decay_all(amount=0.02)
                    logger.info("LifeLoop: Triggered periodic belief confidence decay")
                except Exception as bde:
                    logger.warning("LifeLoop failed to decay beliefs: %s", bde)

                # ── Sleep until next check ─────────────────────────────────
                await asyncio.sleep(decision.next_check_seconds)

            except asyncio.CancelledError:
                logger.info("LifeLoop: Cancelled")
                break
            except Exception as e:
                logger.error(f"LifeLoop: Error in cycle — {e}")
                await asyncio.sleep(60)   # backoff on error

        logger.info("LifeLoop: Exited")

    async def _run_periodic_decay(self) -> None:
        """Run belief decay periodically (e.g. every 60 seconds) in the background."""
        logger.info("LifeLoop: Starting periodic belief decay worker")
        while self._running:
            try:
                await asyncio.sleep(60)
                from belief.belief_updater import belief_updater
                belief_updater.decay_all(amount=0.01)
                logger.info("LifeLoop: Triggered background periodic belief decay")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("LifeLoop periodic decay worker failed: %s", e)


# ── Global singleton ───────────────────────────────────────────────────────────
life_loop = LifeLoop()
