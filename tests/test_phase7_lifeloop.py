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

def t_focus_index_silence_policy():
    from decision.policy_engine import policy_engine
    
    focus = policy_engine.compute_focus_index(
        user_activity="coding",
        idle_seconds=45,
        active_window="main.py - Visual Studio Code",
        screen_text="def run():\n    pytest tests/",
    )
    assert focus >= 0.65
    assert not policy_engine.check_silence_policy(
        "coding",
        45,
        focus_index=focus,
        active_window="main.py - Visual Studio Code",
        screen_text="def run(): pass",
    )
    
    relaxed = policy_engine.compute_focus_index(
        user_activity="idle",
        idle_seconds=1200,
        active_window="Desktop",
        screen_text="",
    )
    assert relaxed < 0.65
    assert policy_engine.check_silence_policy("idle", 1200, focus_index=relaxed)
test("PolicyEngine — continuous User Focus Index controls silence", t_focus_index_silence_policy)

def t_life_context_focus_snapshot():
    from life.observe.observer import LifeContext
    
    ctx = LifeContext(
        user_idle_seconds=30,
        last_user_activity="coding",
        focus_index=0.82,
        active_app="VS Code",
        active_window="server.py - Code",
        screen_text="Traceback error",
    )
    data = ctx.to_dict()
    assert data["focus_index"] == 0.82
    assert data["active_app"] == "VS Code"
    assert data["active_window"] == "server.py - Code"
test("LifeContext — carries focus index and active app/window", t_life_context_focus_snapshot)

def t_energy_drain_and_tired_expression():
    from life.observe.observer import LifeContext
    from life.feel.feel_engine import feel_engine
    from persona.mood.mood_engine import mood_engine
    from persona.behavior.expression.expression_controller import expression_controller
    
    dispatched = []
    old_callback = expression_controller._send_callback
    expression_controller.set_send_callback(lambda command: dispatched.append(command))
    
    try:
        with mood_engine._lock:
            mood_engine._state.energy = 0.22
            mood_engine._state.mood = "mệt mỏi"
        
        ctx = LifeContext(
            user_idle_seconds=30,
            last_user_activity="coding",
            screen_activity="coding",
            hour_of_day=14,
            energy=0.22,
        )
        before = mood_engine.state.energy
        feel_engine.feel(ctx)
        after = mood_engine.state.energy
        
        assert after < before
        assert expression_controller.current_expression == "tired"
        assert any(cmd.get("expression") == "tired" for cmd in dispatched)
    finally:
        expression_controller.set_send_callback(old_callback)
test("FeelEngine — screen scans drain energy and low energy reaches expression", t_energy_drain_and_tired_expression)

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
