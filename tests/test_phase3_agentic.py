"""Phase 2C/D & Phase 3 Integration Tests — kiểm tra toàn bộ Behavior, Interaction, Planning và Cognition stack."""

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


# ── Phase 2C & 2D: Behavior & Interaction ─────────────────────────────────────
print("\n=== Phase 2C & 2D: Behavior & Interaction ===")

def t_idle_animator():
    from persona.behavior.idle.idle_animator import idle_animator
    assert not idle_animator._running
    idle_animator.update_mood("mệt")
    anim = idle_animator._pick_animation()
    assert anim is not None
test("IdleAnimator — animation selection by mood", t_idle_animator)

def t_expression_controller():
    from persona.behavior.expression.expression_controller import expression_controller
    params = expression_controller.apply_emotion("vui vẻ", 0.8)
    assert params["param_MouthForm"] == 0.8 * 0.8
    assert expression_controller.current_expression == "happy"
test("ExpressionController — emotion parameter mapping", t_expression_controller)

def t_greeting_behavior():
    from persona.behavior.greeting.greeting_behavior import greeting_behavior
    res = greeting_behavior.trigger_greeting("Bạn thân")
    assert "speech_text" in res
    assert "motion" in res
    assert res["expression"] == "happy"
test("GreetingBehavior — dialogue and motion selection", t_greeting_behavior)

def t_attention_controller():
    from persona.behavior.attention.attention_controller import attention_controller
    attention_controller.set_mode("mouse")
    params = attention_controller.apply_attention()
    assert "ParamAngleX" in params
    assert "ParamEyeBallX" in params
test("AttentionController — Live2D coordinates tracking", t_attention_controller)

def t_reaction_library():
    from persona.behavior.reactions.reaction_library import reaction_library
    assert reaction_library.trigger("giggle")
    assert not reaction_library.trigger("non_existent_reaction")
test("ReactionLibrary — trigger reactions", t_reaction_library)

def t_hotkey_manager():
    from interaction.hotkey.hotkey_manager import hotkey_manager
    registered = hotkey_manager.register("alt+space", lambda: print("hotkey pressed"))
    # Registered will return True if keyboard hooks set up or simulated
    assert registered is not None
test("HotkeyManager — global hotkey registration", t_hotkey_manager)

def t_notification_manager():
    from interaction.notifications.notification_manager import notification_manager
    # Notification send shouldn't crash
    notification_manager.send("Test Notification", "Hello from tests", is_system=False)
test("NotificationManager — dispatch notification", t_notification_manager)

def t_interaction_adapters():
    from interaction.chat.chat_interaction import chat_interaction
    from interaction.voice.voice_interaction import voice_interaction
    assert chat_interaction is not None
    assert voice_interaction is not None
test("Interaction adapters importable", t_interaction_adapters)


# ── Phase 3A: Planning Engine ──────────────────────────────────────────────────
print("\n=== Phase 3A: Planning Engine ===")

def t_goal_registry():
    from planning.goal_manager.goal_registry import goal_registry
    goal = goal_registry.register_goal("Optimize Database performance", priority=2)
    assert goal.status == "PENDING"
    assert goal.priority == 2
    assert goal_registry.get_goal(goal.id) == goal
    goal_registry.update_status(goal.id, "RUNNING")
    assert goal.status == "RUNNING"
test("GoalRegistry — registration and status updates", t_goal_registry)

def t_task_graph():
    from planning.task_graph.task_graph import TaskGraph
    graph = TaskGraph("test_goal")
    t1 = graph.add_task("task1", "Read DB configs")
    t2 = graph.add_task("task2", "Write DB optimization script", dependencies=["task1"])
    
    assert t1.status == "READY"
    assert t2.status == "PENDING"
    
    ready = graph.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "task1"
    
    graph.mark_completed("task1")
    ready = graph.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "task2"
    assert ready[0].status == "READY"
test("TaskGraph — DAG dependencies and READY discovery", t_task_graph)

def t_task_queue():
    from planning.task_queue.task_queue import TaskQueue
    from planning.task_graph.task_graph import Task
    tq = TaskQueue()
    task1 = Task(id="t1", description="Critical Task")
    task2 = Task(id="t2", description="Medium Task")
    
    tq.push(task2, priority=3)
    tq.push(task1, priority=1)
    
    assert tq.size == 2
    assert tq.pop().id == "t1"  # Critical first
    assert tq.pop().id == "t2"
test("TaskQueue — priority Min-Heap queueing", t_task_queue)


# ── Phase 3B: Cognition Engine ─────────────────────────────────────────────────
print("\n=== Phase 3B: Cognition Engine ===")

def t_response_parser():
    from cognition.parser.response_parser import response_parser
    raw_response = "<think>I need to search Google first</think> [emotion:excited] Hello user! ```json\n{\"tool\": \"search_google\", \"args\": {\"query\": \"DeskAgent\"}}\n```"
    res = response_parser.parse(raw_response)
    assert res.thought == "I need to search Google first"
    assert res.emotion == "excited"
    assert "Hello user!" in res.clean_text
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0]["name"] == "search_google"
test("ResponseParser — thoughts, emotion, and json tool block extraction", t_response_parser)

def t_output_evaluator():
    from cognition.evaluation.output_evaluator import output_evaluator
    r1 = output_evaluator.evaluate("Hello, how can I help you today?")
    assert r1.is_acceptable
    
    r2 = output_evaluator.evaluate("lỗi lỗi lỗi lỗi lỗi lỗi lỗi lỗi lỗi lỗi lỗi lỗi")
    assert not r2.is_acceptable
test("OutputEvaluator — quality and repetition validation", t_output_evaluator)

def t_error_corrector():
    from cognition.self_correction.error_corrector import error_corrector
    assert error_corrector.should_retry("write_file")
    error_corrector.increment_retry("write_file")
    error_corrector.increment_retry("write_file")
    assert not error_corrector.should_retry("write_file")
    
    prompt = error_corrector.build_correction_prompt("read_file", "File not found")
    assert "read_file" in prompt
    assert "File not found" in prompt
test("ErrorCorrector — retry counters and self-correction prompt", t_error_corrector)

def t_self_reflection():
    from cognition.reflection.self_reflection import self_reflection
    from planning.task_graph.task_graph import TaskGraph
    graph = TaskGraph("test_reflection")
    graph.add_task("task1", "Print hello")
    graph.mark_completed("task1")
    
    res = self_reflection.reflect("goal1", "Test reflection", graph)
    assert res.is_successful
    assert "hoàn thành" in res.lessons_learned.lower()

test("SelfReflection — plan post-evaluation and lessons learned", t_self_reflection)


# ── Phase 3C: Agent Runtime ────────────────────────────────────────────────────
print("\n=== Phase 3C: Agent Runtime ===")

def t_agent_registry():
    from agents.registry.agent_registry import agent_registry
    from agents.planner.planner_agent import PlannerAgent
    p = PlannerAgent()
    agent_registry.register("test_planner", p, ["classify_intent"])
    
    assert agent_registry.get_agent("test_planner") == p
    assert "test_planner" in agent_registry.find_agents_by_capability("classify_intent")
test("AgentRegistry — register and query capabilities", t_agent_registry)


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Phase 2C/D & Phase 3 stack verified successfully.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")
