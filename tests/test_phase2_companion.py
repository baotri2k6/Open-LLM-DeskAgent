"""Smoke test for Phase 2 Companion Intelligence modules."""
import sys
sys.path.insert(0, ".")

errors = []

def test(name, fn):
    try:
        fn()
        print(f"[PASS] {name}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        errors.append(name)

# CharacterProfile
def test_character_profile():
    from persona.identity.character_profile import CharacterProfile
    p = CharacterProfile.default()
    assert p.name == "IceGirl"
    assert p.get_trait("cheerful") == 0.9
    p2 = CharacterProfile.from_yaml({
        "name": "Test", "personality": {"cheerful": 0.7}, "tts": {}
    })
    assert p2.name == "Test"
test("CharacterProfile", test_character_profile)

# EmotionClassifier
def test_emotion_classifier():
    from persona.emotion.emotion_classifier import classify_emotion
    emotion, conf = classify_emotion("wow tuyet voi qua!")
    assert emotion in ("excited", "happy", "surprised", "neutral")
    emotion2, _ = classify_emotion("buon qua hom nay")
    assert emotion2 in ("sad", "bored", "neutral")
test("EmotionClassifier", test_emotion_classifier)

# EmotionMapper
def test_emotion_mapper():
    from persona.emotion.emotion_mapper import get_expression, get_motion, get_avatar_hints
    assert get_expression("happy") == "exp_happy"
    assert get_motion("sad") == "motion_sad"
    hints = get_avatar_hints("excited")
    assert hints["emotion"] == "excited"
test("EmotionMapper", test_emotion_mapper)

# EmotionEngine
def test_emotion_engine():
    from persona.emotion.emotion_engine import EmotionEngine
    eng = EmotionEngine()
    eng.update_from_user_text("hom nay vui ve lam!")
    snap = eng.snapshot()
    assert "emotion" in snap
    assert "intensity" in snap
    eng.update_from_event("task_success")
    assert eng.emotion in ("proud", "happy", "excited", "neutral")
test("EmotionEngine", test_emotion_engine)

# PersonalityProfile
def test_personality_profile():
    from persona.behavior.personality import PersonalityProfile
    pp = PersonalityProfile.default()
    assert pp.name == "IceGirl"
    assert 0 <= pp.energy_level <= 1
    assert 0 <= pp.social_warmth <= 1
test("PersonalityProfile", test_personality_profile)

# MoodState
def test_mood_state():
    from persona.mood.mood_states import MoodState
    m = MoodState()
    assert m.mood == "vui vẻ"
    assert 0 <= m.overall_wellbeing <= 1
    d = m.to_dict()
    assert "wellbeing" in d
    m2 = MoodState.from_dict(d)
    assert m2.energy == m.energy
test("MoodState", test_mood_state)

# RelationshipLevels
def test_relationship_levels():
    from persona.relationship.relationship_levels import score_to_level
    assert score_to_level(0)   == "Người lạ"
    assert score_to_level(100) == "Người quen"
    assert score_to_level(500) == "Bạn thân"
test("RelationshipLevels", test_relationship_levels)

# DailyGoals
def test_daily_goals():
    from persona.goals.daily_goals import pick_daily_goals
    goals = pick_daily_goals(n=3, seed=20260627)
    assert 1 <= len(goals) <= 3
    assert all("id" in g for g in goals)
test("DailyGoals", test_daily_goals)

# LifeObserver
def test_life_observer():
    from life.observe.observer import LifeObserver
    obs = LifeObserver()
    obs.record_user_message()
    ctx = obs.observe(mood="vui vẻ", emotion="happy", energy=0.8)
    assert ctx.hour_of_day >= 0
    assert ctx.user_idle_seconds >= 0
    assert ctx.mood == "vui vẻ"
test("LifeObserver", test_life_observer)

# DecisionEngine
def test_decision_engine():
    from life.decide.decision_engine import DecisionEngine
    from life.observe.observer import LifeContext
    de = DecisionEngine()
    ctx = LifeContext(hour_of_day=14, user_idle_seconds=10)
    dec = de.decide(ctx)
    assert hasattr(dec, "should_act")
    assert hasattr(dec, "next_check_seconds")
    assert dec.next_check_seconds > 0
test("DecisionEngine", test_decision_engine)

# PersonaManager
def test_persona_manager():
    from persona.persona_manager import PersonaManager
    pm = PersonaManager()
    profile = pm.get_character_profile("icegirl")
    # Should return either a real profile or the default fallback
    assert profile.name != ""
    assert profile.get_trait("cheerful") >= 0.0
test("PersonaManager", test_persona_manager)

# Summary
print()
if errors:
    print(f"FAILED: {len(errors)} tests — {errors}")
    sys.exit(1)
else:
    print(f"ALL {10 - len(errors)}/10 TESTS PASSED")
