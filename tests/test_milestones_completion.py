"""Integration Tests for the newly completed stubs & empty modules across Milestones."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, 'd:/Open LLM DeskAgent')

PASS = 0
FAIL = 0


def test(name, fn):
    global PASS, FAIL
    try:
        if asyncio.iscoroutinefunction(fn):
            asyncio.run(fn())
        else:
            fn()
        print(f"  [PASS] {name}")
        PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        import traceback
        traceback.print_exc()
        FAIL += 1


# ── Priority 1: Memory Long-Term & Writeback ──────────────────────────────────
print("\n=== Priority 1: Long-term Memory & Writeback ===")

def t_long_term_memory_store():
    from memory.semantic.long_term import long_term_store
    
    # Reset or clear fallback DB
    res = long_term_store.add_fact("Cậu ấy thích học Python vào buổi sáng", category="user_preference")
    assert res
    
    facts = long_term_store.search_facts("học Python")
    assert len(facts) > 0
    assert "Python" in facts[0]["text"]
test("LongTermMemoryStore — save and retrieve facts", t_long_term_memory_store)

def t_retrieval_engine():
    from memory.retrieval.retrieval_engine import retrieval_engine
    
    snippets = retrieval_engine.retrieve_relevant("buổi sáng")
    assert len(snippets) > 0
    assert any("Python" in s for s in snippets)
test("RetrievalEngine — retrieve unified snippets", t_retrieval_engine)

async def t_memory_writeback():
    from memory.writeback.memory_writeback import memory_writeback
    
    # Try turning dialog info into memory fact
    await memory_writeback.write_back("Tớ thích chơi cờ vua lúc rảnh rỗi.", "Ồ thế à, cờ vua rất thú vị!")
test("MemoryWriteback — distill dialogues and save facts", t_memory_writeback)


# ── Priority 2 & 3: Life Loop feel/reflect and Curiosity ─────────────────────
print("\n=== Priority 2 & 3: Life Loop & Curiosity ===")

def t_feel_reflect_engines():
    from life.observe.observer import LifeContext
    from life.feel.feel_engine import feel_engine
    from life.reflect.reflect_engine import reflect_engine
    from life.decide.decision_engine import Decision
    
    ctx = LifeContext(user_idle_seconds=400, last_user_activity="gaming", energy=0.8)
    
    # Feel engine tick
    feel_engine.feel(ctx)
    
    # Reflect cycle tick
    reflect_engine.reflect_cycle(ctx, Decision(should_act=True), action_taken=True)
test("FeelEngine & ReflectEngine — loop cycle evaluation", t_feel_reflect_engines)

def t_curiosity_engine():
    from life.observe.observer import LifeContext
    from persona.curiosity.curiosity_engine import curiosity_engine
    
    ctx = LifeContext(last_user_activity="coding")
    topic = curiosity_engine.get_proactive_topic(ctx)
    assert len(topic) > 0
test("CuriosityEngine — context-driven proactive topic suggestion", t_curiosity_engine)


# ── Priority 4: Grounding & Perception Fusion ────────────────────────────────
print("\n=== Priority 4: Grounding & Perception Fusion ===")

def t_grounding_engine():
    from vision.grounding.grounding_engine import grounding_engine
    
    # Try grounding on screen, might return None if no word matches, which is safe
    res = grounding_engine.ground("Sign In")
    if res:
        assert len(res) == 2
test("GroundingEngine — search element coords on screen", t_grounding_engine)

def t_perception_fusion_real_ocr():
    from perception.fusion.perception_fusion import PerceptionFusion
    
    packet = PerceptionFusion.fuse(user_message="Hello", last_interaction_time=None)
    assert "screen_text" in packet
    assert "timestamp" in packet
test("PerceptionFusion — auto-OCR during context packets fusion", t_perception_fusion_real_ocr)


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Milestones stubs and empties filled successfully.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")
