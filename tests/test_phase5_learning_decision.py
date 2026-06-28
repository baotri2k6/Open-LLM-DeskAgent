"""Phase 5 Integration Tests — kiểm tra Belief, Learning và Decision stack."""

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


# ── Phase 5: Belief Store & User Model ─────────────────────────────────────────
print("\n=== Phase 5: Belief & User Model ===")

def t_belief_store():
    from belief.belief_store import belief_store
    b = belief_store.set_belief("user.preference.editor", "vscode", confidence=0.9)
    assert b.key == "user.preference.editor"
    assert b.value == "vscode"
    assert b.confidence == 0.9
    
    b2 = belief_store.get_belief("user.preference.editor")
    assert b2 == b
    
    belief_store.decay_confidence("user.preference.editor", 0.1)
    assert round(b.confidence, 1) == 0.8
test("BeliefStore — register, query, and decay beliefs", t_belief_store)

def t_user_model():
    from belief.user_model import user_model
    user_model.set_preference("theme", "dark")
    assert user_model.get_preference("theme") == "dark"
    
    user_model.set_user_trait("night_owl", active=True, confidence=0.8)
    assert "night_owl" in user_model.get_user_traits()
test("UserModel — preference and trait management", t_user_model)


# ── Phase 5: Experience & Learning ─────────────────────────────────────────────
print("\n=== Phase 5: Experience & Learning ===")

def t_experience_store():
    from learning.experience.experience_store import experience_store
    exp = experience_store.record_experience("goal1", "Test database repair", is_successful=True, lessons_learned="Database backup restored successfully")
    assert exp.is_successful
    assert len(experience_store.get_recent_experiences()) >= 1
test("ExperienceStore — record and retrieve experiences", t_experience_store)

def t_reflection_engine():
    from learning.reflection.reflection_engine import reflection_engine
    from planning.task_graph.task_graph import TaskGraph
    graph = TaskGraph("test_reflect")
    graph.add_task("task1", "Run command")
    graph.mark_completed("task1")
    
    res = reflection_engine.reflect_on_goal("goal2", "Run simple command", graph)
    assert res["success"]
    assert "completed" in res["lessons"].lower()
test("ReflectionEngine — deduct environment beliefs on failure", t_reflection_engine)


# ── Phase 5: Decision Layer ───────────────────────────────────────────────────
print("\n=== Phase 5: Decision Layer ===")

def t_intention_manager():
    from decision.intention_manager import intention_manager
    intent = intention_manager.set_active_intention("debug_app", "task", priority=2)
    assert intent.name == "debug_app"
    assert intention_manager.get_highest_intention().name == "debug_app"
    
    intention_manager.clear_intention("debug_app")
    assert intention_manager.get_highest_intention().name == "casual_connection"
test("IntentionManager — priority queueing of active intentions", t_intention_manager)

def t_priority_manager():
    from decision.priority_manager import priority_manager
    assert priority_manager.resolve_priority("critical error occurred") == 1
    assert priority_manager.resolve_priority("writing code in python") == 2
    assert priority_manager.resolve_priority("chatting casually") == 4
test("PriorityManager — contextual priority resolution", t_priority_manager)

def t_risk_assessment():
    from decision.risk_assessment import risk_assessment
    res1 = risk_assessment.assess("execute_command", {"command": "rm -rf /"})
    assert res1["risk_level"] == "high"
    assert res1["is_dangerous"]
    
    res2 = risk_assessment.assess("read_file", {"path": "test.txt"})
    assert res2["risk_level"] == "low"
test("RiskAssessment — command and file risk classification", t_risk_assessment)

def t_policy_engine():
    from decision.policy_engine import policy_engine
    # Silence policy: busy user -> stay silent (False)
    assert not policy_engine.check_silence_policy("coding", 100)
    # Idle user -> ok to talk (True)
    assert policy_engine.check_silence_policy("idle", 400)
test("PolicyEngine — Silence Policy enforcement", t_policy_engine)

def t_action_selector():
    from decision.action_selector import action_selector
    eval1 = action_selector.evaluate_action("execute_command", {"command": "git status"}, "coding", 20)
    assert eval1["allow"]
    assert eval1["requires_approval"]  # Default auto_safe requires approval for command executions
test("ActionSelector — evaluate risk and approval requirements", t_action_selector)


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Phase 5 Learning & Decision stack verified successfully.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")
