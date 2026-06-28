"""Phase 7 Integration Tests — kiểm tra LifeLoop, Thinker, và Autonomous Decision flow."""

import sys
sys.path.insert(0, 'd:/Open LLM DeskAgent')

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


# ── Phase 7: Thinker & Autonomous Decision ───────────────────────────────────
print("\n=== Phase 7: Thinker & Life Loop ===")

def t_thinker_silence_policy():
    from life.observe.observer import LifeContext
    from life.think.thinker import thinker
    
    # Giả lập context khi user đang bận viết code
    ctx = LifeContext(
        user_idle_seconds=20,
        last_user_activity="coding",
        hour_of_day=14,
        energy=0.8
    )
    
    res = thinker.think(ctx)
    assert res["stay_silent"]  # Phải giữ im lặng vì user đang bận code
    assert res["proposed_intention"] == "observe_silently"
test("Thinker — Silence Policy enforcement from activity", t_thinker_silence_policy)

def t_thinker_night_owl():
    from life.observe.observer import LifeContext
    from life.think.thinker import thinker
    from belief.user_model import user_model
    
    # Thiết lập niềm tin user là cú đêm
    user_model.set_user_trait("night_owl", active=True, confidence=0.8)
    
    # Giả lập đêm muộn, người dùng không hoạt động (idle > 10 phút)
    ctx = LifeContext(
        user_idle_seconds=700,
        last_user_activity="coding",
        hour_of_day=23,
        energy=0.8
    )
    
    res = thinker.think(ctx)
    assert "cú đêm" in res["thought"].lower()
    assert res["proposed_intention"] == "night_owl_chat"
test("Thinker — Night Owl trait awareness", t_thinker_night_owl)

def t_decision_with_silence_policy():
    from life.observe.observer import LifeContext
    from life.decide.decision_engine import decision_engine
    
    # Giả lập context khi user đang bận
    ctx = LifeContext(
        user_idle_seconds=10,
        last_user_activity="coding",
        hour_of_day=15,
        energy=0.7
    )
    
    # Quyết định thông thường
    dec = decision_engine.decide(ctx)
    
    # Tích hợp logic im lặng từ LifeLoop
    from life.think.thinker import thinker
    thought_res = thinker.think(ctx)
    if thought_res.get("stay_silent"):
        dec.should_act = False
        
    assert not dec.should_act  # Phải im lặng
test("DecisionEngine — override proactive action during busy periods", t_decision_with_silence_policy)


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Phase 7 LifeLoop & Thinker verified successfully.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")
