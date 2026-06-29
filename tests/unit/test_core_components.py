"""Unit tests for core components: ContextPacket, BeliefStore, MemoryManager, and EmotionEngine."""

from __future__ import annotations

import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# ── 1. ContextPacket Tests ───────────────────────────────────────────────────

from runtime.context.context_packet import ContextPacket

def test_context_packet_default_initialization() -> None:
    packet = ContextPacket()
    assert packet.user_message == ""
    assert packet.ocr_text == ""
    assert packet.activity == "unknown"
    assert packet.idle_seconds == 0.0
    assert packet.active_window == "unknown"
    assert isinstance(packet.hour_of_day, int)
    assert packet.metadata == {}

def test_context_packet_custom_fields() -> None:
    packet = ContextPacket(
        user_message="Hello!",
        ocr_text="Google Chrome window",
        activity="browsing",
        idle_seconds=5.5,
        active_window="Chrome",
        metadata={"key": "val"}
    )
    assert packet.user_message == "Hello!"
    assert packet.ocr_text == "Google Chrome window"
    assert packet.activity == "browsing"
    assert packet.idle_seconds == 5.5
    assert packet.active_window == "Chrome"
    assert packet.metadata == {"key": "val"}

def test_context_packet_to_dict() -> None:
    packet = ContextPacket(
        user_message="Test message",
        ocr_text="some ocr text",
        activity="coding",
        idle_seconds=10.0,
        active_window="VS Code",
        metadata={"custom_flag": True}
    )
    d = packet.to_dict()
    assert d["user_message"] == "Test message"
    assert d["screen_text"] == "some ocr text"
    assert d["idle_time_seconds"] == 10.0
    assert d["activity"] == "coding"
    assert d["active_window"] == "VS Code"
    assert d["custom_flag"] is True

def test_context_packet_get_and_getitem() -> None:
    packet = ContextPacket(user_message="Hello World", active_window="Notepad")
    assert packet.get("user_message") == "Hello World"
    assert packet.get("active_window") == "Notepad"
    assert packet.get("nonexistent", "default") == "default"
    assert packet["user_message"] == "Hello World"
    assert packet["active_window"] == "Notepad"

def test_context_packet_contains() -> None:
    packet = ContextPacket(user_message="Help", metadata={"extra": 42})
    assert "user_message" in packet
    assert "screen_text" in packet  # maps from ocr_text in to_dict()
    assert "extra" in packet
    assert "nonexistent_field" not in packet


# ── 2. BeliefStore Tests ──────────────────────────────────────────────────────

from belief.belief_store import BeliefStore, Belief

def test_belief_store_initialization(tmp_path: Path) -> None:
    path = tmp_path / "beliefs.json"
    store = BeliefStore(beliefs_path=path)
    assert len(store.list_all_beliefs()) == 0

def test_belief_store_set_and_get(tmp_path: Path) -> None:
    path = tmp_path / "beliefs.json"
    store = BeliefStore(beliefs_path=path)
    b = store.set_belief("user_editor", "VS Code", confidence=0.8, source="observation")
    assert b.key == "user_editor"
    assert b.value == "VS Code"
    assert b.confidence == 0.8
    assert b.source == "observation"

    retrieved = store.get_belief("user_editor")
    assert retrieved is not None
    assert retrieved.value == "VS Code"

def test_belief_store_clamping(tmp_path: Path) -> None:
    path = tmp_path / "beliefs.json"
    store = BeliefStore(beliefs_path=path)
    b_high = store.set_belief("test_high", "val", confidence=1.5)
    assert b_high.confidence == 1.0

    b_low = store.set_belief("test_low", "val", confidence=-0.5)
    assert b_low.confidence == 0.0

def test_belief_store_decay_confidence(tmp_path: Path) -> None:
    path = tmp_path / "beliefs.json"
    store = BeliefStore(beliefs_path=path)
    store.set_belief("user_pref", "dark_mode", confidence=0.6)
    
    store.decay_confidence("user_pref", amount=0.1)
    b = store.get_belief("user_pref")
    assert b is not None
    assert round(b.confidence, 2) == 0.5

    # decay below 0
    store.decay_confidence("user_pref", amount=1.0)
    assert store.get_belief("user_pref").confidence == 0.0

def test_belief_store_save_and_load(tmp_path: Path) -> None:
    path = tmp_path / "beliefs.json"
    store = BeliefStore(beliefs_path=path)
    store.set_belief("k1", "v1", confidence=0.7, source="direct_feedback")
    
    # Instantiate another store pointing to same path to check load
    store2 = BeliefStore(beliefs_path=path)
    b = store2.get_belief("k1")
    assert b is not None
    assert b.value == "v1"
    assert b.confidence == 0.7
    assert b.source == "direct_feedback"


# ── 3. MemoryManager Tests ────────────────────────────────────────────────────

from memory.memory_manager import MemoryManager

def test_memory_manager_working_memory_flow() -> None:
    mgr = MemoryManager()
    mgr.clear_working_memory()
    assert len(mgr.get_working_memory()) == 0

    mgr.add_turn("user", "Hello companion", emotion="happy")
    mgr.add_turn("assistant", "Hello user!", emotion="friendly")
    
    turns = mgr.get_working_memory(last_n=2)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[0]["content"] == "Hello companion"
    assert turns[1]["role"] == "assistant"
    
    llm_hist = mgr.get_history_for_llm(last_n=2)
    assert len(llm_hist) == 2
    assert llm_hist[0] == {"role": "user", "content": "Hello companion"}

def test_memory_manager_session_lifecycle() -> None:
    mgr = MemoryManager()
    mgr.on_session_start()
    assert len(mgr.get_working_memory()) == 0
    assert mgr._session_summary == ""

    # Mock service to check end session writeback
    mock_svc = MagicMock()
    mgr._service = mock_svc
    mgr.on_session_end(summary="User talked about code design")
    
    assert mgr._session_summary == "User talked about code design"
    mock_svc.remember.assert_called_once_with("User talked about code design", "session_summary")

def test_memory_manager_snapshot() -> None:
    mgr = MemoryManager()
    mgr.clear_working_memory()
    mgr.add_turn("user", "hi")
    snap = mgr.get_state_snapshot()
    assert snap["working_memory_turns"] == 1
    assert "session_duration_s" in snap

def test_memory_manager_user_name_fallback() -> None:
    mgr = MemoryManager()
    # Mock profile service return
    mock_svc = MagicMock()
    mock_svc.get_profile.return_value = {"name": "Alice"}
    mgr._service = mock_svc
    
    assert mgr.get_user_name() == "Alice"

    # Profile empty or none
    mock_svc.get_profile.return_value = {}
    assert mgr.get_user_name() == ""


# ── 4. EmotionEngine Tests ────────────────────────────────────────────────────

from persona.emotion.emotion_engine import EmotionEngine

def test_emotion_engine_default_initialization() -> None:
    eng = EmotionEngine()
    assert eng.emotion == "neutral"
    assert eng.intensity == 0.0

def test_emotion_engine_tagged_emotion() -> None:
    eng = EmotionEngine()
    eng.update_from_tagged_emotion("sad")
    assert eng.emotion == "sad"
    assert eng.intensity == 0.9

def test_emotion_engine_user_text_classification() -> None:
    eng = EmotionEngine()
    # "Tớ rất vui hôm nay" maps to happy with confidence
    eng.update_from_user_text("Tớ rất vui hôm nay")
    assert eng.emotion == "happy"
    assert eng.intensity > 0.0

def test_emotion_engine_ai_text_classification() -> None:
    eng = EmotionEngine()
    # ai text reply classification
    eng.update_from_ai_text("I feel absolutely proud of our progress!")
    # maps to happy/proud
    assert eng.emotion in ["happy", "proud"]
    assert eng.intensity == 0.6

def test_emotion_engine_system_events() -> None:
    eng = EmotionEngine()
    
    eng.update_from_event("user_arrived")
    assert eng.emotion == "happy"
    assert eng.intensity == 0.8

    eng.update_from_event("task_failed")
    # task_failed has weight 0.5, current intensity is 0.8, should override
    assert eng.emotion == "sad"
    assert eng.intensity == 0.5

def test_emotion_engine_reinforcement() -> None:
    eng = EmotionEngine()
    eng.update_from_tagged_emotion("happy")
    initial_intensity = eng.intensity # 0.9
    
    # Reinforce happy
    eng.update_from_tagged_emotion("happy")
    # should increase or remain clamped at 1.0
    assert eng.intensity >= initial_intensity
    assert eng.emotion == "happy"

def test_emotion_engine_override_thresholds() -> None:
    eng = EmotionEngine()
    eng.update_from_tagged_emotion("sad") # intensity = 0.9
    
    # Try updating with a weak event (e.g. idle_short = bored with weight 0.3)
    eng.update_from_event("idle_short")
    assert eng.emotion == "sad"

    # Try updating with a strong event (e.g. user_arrived = happy with weight 0.8)
    eng.update_from_event("user_arrived")
    assert eng.emotion == "happy"

def test_emotion_engine_reset() -> None:
    eng = EmotionEngine()
    eng.update_from_tagged_emotion("proud")
    eng.reset()
    assert eng.emotion == "neutral"
    assert eng.intensity == 0.0


@pytest.mark.anyio
async def test_planner_agent_beliefs_blocking(tmp_path) -> None:
    from belief.belief_store import BeliefStore
    from agents.planner.planner_agent import PlannerAgent
    import belief.belief_store as bs_mod

    # Setup temporary belief store
    test_db = tmp_path / "test_beliefs.json"
    custom_store = BeliefStore(beliefs_path=test_db)
    
    # Mock global belief_store reference
    original_store = bs_mod.belief_store
    bs_mod.belief_store = custom_store
    
    try:
        # Set execute_command as broken
        custom_store.set_belief("env.tool_broken.execute_command", "true", confidence=0.8, source="reflection")
        
        planner = PlannerAgent()
        
        # Test open_app (which resolves to execute_command)
        res = await planner.handle_message("mở terminal")
        
        # Verify it was blocked and marked sad/shake
        assert "execute_command" in res["text"]
        assert res["emotion"] == "sad"
        assert res["avatar"]["motion"] == "shake"
        
    finally:
        bs_mod.belief_store = original_store

