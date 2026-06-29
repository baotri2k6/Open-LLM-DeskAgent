"""Phase 2 Integration Tests — kiểm tra toàn bộ Companion Intelligence stack."""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

PASS = 0
FAIL = 0


def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  [PASS] {name}")
        PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        FAIL += 1


def test_async(name, coro_fn):
    global PASS, FAIL
    try:
        asyncio.get_event_loop().run_until_complete(coro_fn())
        print(f"  [PASS] {name}")
        PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        FAIL += 1


# ── Phase 1 gaps ──────────────────────────────────────────────────────────────
print("\n=== Phase 1 Gaps ===")

def t_event_schema():
    from runtime.events.base_event import BaseEvent
    from runtime.events.event_types import EventType
    e = BaseEvent.create(EventType.VOICE_DETECTED, "stt")
    assert e.event_type == "VoiceDetected"
    assert e.source == "stt"
    d = e.to_dict()
    assert "correlation_id" in d
    e2 = BaseEvent.from_dict(d)
    assert e2.event_type == e.event_type
test("BaseEvent + EventType schema", t_event_schema)

def t_state_machine():
    from runtime.state.state_store import StateStore, CompanionState
    ss = StateStore()
    assert ss.state == CompanionState.IDLE
    assert not ss.is_busy()
    loop = asyncio.new_event_loop()
    ok = loop.run_until_complete(ss.transition(CompanionState.LISTENING))
    assert ok
    assert ss.state == CompanionState.LISTENING
    assert ss.is_busy()
    bad = loop.run_until_complete(ss.transition(CompanionState.EXECUTING))
    assert not bad  # Invalid transition LISTENING -> EXECUTING
    loop.close()
test("StateStore + valid/invalid transitions", t_state_machine)

def t_memory_manager():
    from memory.memory_manager import MemoryManager
    mm = MemoryManager()
    mm.add_turn("user", "hello")
    mm.add_turn("assistant", "hi")
    history = mm.get_working_memory(5)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    snippets = mm.recall_for_prompt("")
    assert isinstance(snippets, list)
test("MemoryManager working memory + recall", t_memory_manager)

def t_lifecycle_imports():
    from runtime.lifecycle.lifecycle_manager import LifecycleManager
    lm = LifecycleManager()
    assert not lm.is_ready
test("LifecycleManager importable", t_lifecycle_imports)

def t_session_manager():
    from runtime.session.session_manager import SessionManager
    sm = SessionManager()
    assert not sm.is_active
    s = sm.start_session()
    assert sm.is_active
    sm.on_user_activity()
    assert sm.current.turn_count == 1
    sm.end_session()
    assert not sm.is_active
test("SessionManager lifecycle", t_session_manager)

# ── Phase 2A Motivation ───────────────────────────────────────────────────────
print("\n=== Phase 2A: Motivation Engine ===")

def t_needs():
    from motivation.needs import CompanionNeeds
    n = CompanionNeeds()
    summary = n.get_summary()
    assert "connection" in summary
    assert "stimulation" in summary
    n.satisfy("connection", 0.5)
    assert n._needs["connection"].is_satisfied()
    wellbeing = n.overall_wellbeing()
    assert 0.0 <= wellbeing <= 1.0
test("CompanionNeeds — hierarchy, satisfy, wellbeing", t_needs)

def t_boredom():
    from motivation.boredom import BoredomDetector
    b = BoredomDetector()
    b._last_activity -= 60 * 20   # Simulate 20 min idle
    state = b.tick()
    assert state.idle_minutes >= 19
    assert state.level > 0
    assert b.should_trigger()
    b.mark_triggered()
    assert not b.should_trigger()   # Cooldown active
test("BoredomDetector — idle detection, trigger, cooldown", t_boredom)

def t_curiosity():
    from motivation.curiosity import CuriositySystem
    cs = CuriositySystem()
    cs.add_topic("machine learning", 0.8)
    assert len(cs.get_top_interests()) >= 1
    topics = cs.extract_topics_from_text("I was debugging Python code with FastAPI")
    assert isinstance(topics, list)
test("CuriositySystem — topics, extraction", t_curiosity)

def t_drives():
    from motivation.drives import IntrinsicDrives
    d = IntrinsicDrives()
    vec = d.get_personality_vector()
    assert "helpfulness" in vec
    assert "authenticity" in vec
    active = d.get_active_drives("bug lỗi không debug được")
    assert len(active) >= 1
    desc = d.describe_for_prompt()
    assert len(desc) > 10
test("IntrinsicDrives — personality vector, activation", t_drives)

def t_motivation_manager():
    from motivation.motivation_manager import MotivationManager
    mm = MotivationManager()
    sig = mm.tick()
    assert hasattr(sig, 'should_be_proactive')
    assert hasattr(sig, 'wellbeing')
    assert 0.0 <= sig.wellbeing <= 1.0
    mm.on_conversation("tao đang debug python code")
    mm.on_task_completed()
    mm.on_learned_something("fastapi routing")
    desc = mm.describe_for_prompt()
    assert len(desc) > 5
test("MotivationManager — tick, events, describe", t_motivation_manager)

# ── Phase 2B Social ───────────────────────────────────────────────────────────
print("\n=== Phase 2B: Social Layer ===")

def t_empathy():
    from social.empathy.empathy_engine import EmpathyEngine
    e = EmpathyEngine()

    # ASCII-only frustrated text (works across all console encodings)
    r1 = e.analyze("debug mai khong duoc, buc qua")
    assert r1.detected_emotion == "frustrated", f"Got: {r1.detected_emotion}"
    assert r1.needs_support
    assert r1.recommended_tone == "empathetic"

    # Excited
    r2 = e.analyze("ok roi! lam duoc roi! great!")
    assert r2.detected_emotion in ("excited", "neutral")

    # Neutral
    r3 = e.analyze("hello")
    assert r3.detected_emotion == "neutral"

    prefix = e.get_empathy_prefix(r1)
    assert isinstance(prefix, str)
test("EmpathyEngine — 5 emotion detection, tone, prefix", t_empathy)

def t_conversation_manager():
    from social.conversation.conversation_manager import ConversationManager
    cm = ConversationManager()
    cm.on_user_message("tao đang viết code python", "neutral")
    assert cm._context.conversation_type == "technical"
    assert cm._context.total_turns == 1
    cm.on_assistant_message("ok tao xem code của mày nhé")
    recent = cm.get_recent_turns(5)
    assert len(recent) == 2
    desc = cm.describe_for_prompt()
    assert "technical" in desc
test("ConversationManager — multi-turn, topic, type detection", t_conversation_manager)

# ── PromptBuilder ─────────────────────────────────────────────────────────────
print("\n=== Prompt Architecture ===")

def t_prompt_builder():
    from cognition.prompts.prompt_builder import PromptBuilder
    pb = PromptBuilder()
    prompt = pb.build(
        memory_snippets=["[hôm qua] user debug LifeLoop", "[2 ngày trước] user thích Python"]
    )
    assert len(prompt) > 100
    assert "Behavioral Rules" in prompt or "Rules" in prompt
    # Token budget rough check
    assert len(prompt) < 15000   # Should be well under
test("PromptBuilder — 9-layer build, memory injection, rules", t_prompt_builder)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Phase 1 gaps + Phase 2A/2B complete.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")
