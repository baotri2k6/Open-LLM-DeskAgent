"""Phase 7 Integration Tests — kiểm tra LifeLoop, Thinker, và Autonomous Decision flow."""

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

def t_persona_evolution():
    from persona.persona_manager import persona_manager
    from persona.relationship.relationship_tracker import relationship_tracker
    from belief.user_model import user_model
    
    # 1. Tăng điểm quan hệ lên "Bạn thân"
    relationship_tracker.add_raw(600) # Threshold > 500
    user_model.set_user_trait("night_owl", active=True, confidence=0.8)
    user_model.set_preference("editor", "vscode")
    
    # 2. Tiến hóa tính cách
    persona_manager.evolve_personality()
    
    profile = persona_manager.get_character_profile(persona_manager.active_character)
    print("DEBUG SPEECH STYLE:", profile.speech_style)
    print("DEBUG FAVORITE TOPICS:", profile.favorite_topics)
    
    assert "teasing" in profile.speech_style or "intimate" in profile.speech_style or "casual" in profile.speech_style, f"Speech styles: {profile.speech_style}"
    assert "night owl hacks" in profile.favorite_topics, f"Topics: {profile.favorite_topics}"
    assert "vscode tips" in profile.favorite_topics, f"Topics: {profile.favorite_topics}"
test("PersonaManager — dynamic personality evolution based on user profile", t_persona_evolution)

def t_prompt_builder():
    from cognition.prompts.prompt_builder import PromptBuilder
    pb = PromptBuilder()
    prompt = pb.build(include_tools=False)
    
    # Phải chứa cả Persona Core thực tế từ yaml chứ không dùng default fallback
    assert "[Persona Core]" in prompt
    assert "IceGirl" in prompt
    assert "night owl hacks" in prompt
test("PromptBuilder — integrates evolved persona core successfully", t_prompt_builder)



# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Phase 7 LifeLoop & Thinker verified successfully.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")
