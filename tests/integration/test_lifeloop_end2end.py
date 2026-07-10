"""End-to-end integration test for the autonomous Life Loop cycle."""

from __future__ import annotations

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from life.life_loop import LifeLoop
from life.observe.observer import LifeContext


@pytest.mark.anyio
async def test_lifeloop_single_cycle() -> None:
    # 1. Setup ws_clients mock
    ws_clients = set()
    loop = LifeLoop(ws_clients)
    
    # 2. Mock cycle components to track calls and avoid external dependencies
    from life.observe.observer import life_observer
    from life.decide.decision_engine import decision_engine
    from life.act.proactive_messenger import proactive_messenger
    from life.think.thinker import thinker
    
    original_observe = life_observer.observe
    original_decide = decision_engine.decide
    original_send = proactive_messenger.send
    original_think = thinker.think
    
    # Construct a real LifeContext instance to avoid MagicMock comparison exceptions
    mock_context = LifeContext(
        hour_of_day=14,  # Afternoon, so is_late_night() is False
        user_idle_seconds=10.0,
        last_user_activity="coding",
        mood="vui vẻ",
        emotion="neutral",
        energy=0.7
    )
    
    life_observer.observe = MagicMock(return_value=mock_context)
    
    mock_decision = MagicMock()
    mock_decision.should_act = True
    mock_decision.action_type = "chat"
    mock_decision.message_hint = "Proactive checkin"
    mock_decision.next_check_seconds = 1
    
    decision_engine.decide = MagicMock(return_value=mock_decision)
    proactive_messenger.send = AsyncMock(return_value=True)
    thinker.think = MagicMock(return_value={"stay_silent": False})
    
    # Track reflect engine calls
    from life.reflect.reflect_engine import reflect_engine
    original_reflect = reflect_engine.reflect_cycle
    reflect_engine.reflect_cycle = MagicMock()
    
    # Helper to stop loop inside asyncio.sleep without recursion
    async def mock_sleep(seconds):
        loop.stop()

    try:
        # Patch sleep to immediately terminate loop after first cycle
        with patch("asyncio.sleep", side_effect=mock_sleep):
            # Run one cycle of LifeLoop
            await loop.start_async()
            
    finally:
        # Clean up global singleton mocks
        life_observer.observe = original_observe
        decision_engine.decide = original_decide
        proactive_messenger.send = original_send
        thinker.think = original_think
        reflect_engine.reflect_cycle = original_reflect
        loop.stop()


@pytest.mark.anyio
async def test_lifeloop_direct_run_cycle() -> None:
    # 1. Setup loop
    loop = LifeLoop()
    
    # 2. Mock components
    from life.observe.observer import life_observer
    from life.decide.decision_engine import decision_engine
    from life.act.proactive_messenger import proactive_messenger
    from life.think.thinker import thinker
    
    original_observe = life_observer.observe
    original_decide = decision_engine.decide
    original_send = proactive_messenger.send
    original_think = thinker.think
    
    # Construct a real LifeContext instance
    mock_context = LifeContext(
        hour_of_day=14,  # Afternoon
        user_idle_seconds=10.0,
        last_user_activity="coding",
        mood="vui vẻ",
        emotion="neutral",
        energy=0.7
    )
    
    life_observer.observe = MagicMock(return_value=mock_context)
    
    mock_decision = MagicMock()
    mock_decision.should_act = True
    mock_decision.action_type = "chat"
    mock_decision.message_hint = "Proactive checkin"
    mock_decision.next_check_seconds = 1
    
    decision_engine.decide = MagicMock(return_value=mock_decision)
    proactive_messenger.send = AsyncMock(return_value=True)
    thinker.think = MagicMock(return_value={"stay_silent": False})
    
    from life.reflect.reflect_engine import reflect_engine
    original_reflect = reflect_engine.reflect_cycle
    reflect_engine.reflect_cycle = MagicMock()
    
    # Track sleep call
    sleep_called = False
    async def mock_sleep(seconds):
        nonlocal sleep_called
        sleep_called = True
        loop.stop() # Set running = False to exit the loop

    try:
        loop._running = True
        with patch("asyncio.sleep", side_effect=mock_sleep):
            await loop._run()
            
        assert sleep_called is True
        life_observer.observe.assert_called_once()
        decision_engine.decide.assert_called_once_with(mock_context)
        proactive_messenger.send.assert_called_once_with(
            action_type="chat",
            message_hint="Proactive checkin"
        )
        reflect_engine.reflect_cycle.assert_called_once_with(mock_context, mock_decision, True)
        
    finally:
        life_observer.observe = original_observe
        decision_engine.decide = original_decide
        proactive_messenger.send = original_send
        thinker.think = original_think
        reflect_engine.reflect_cycle = original_reflect
        loop.stop()
