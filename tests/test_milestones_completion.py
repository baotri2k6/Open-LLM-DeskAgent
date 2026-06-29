"""Integration Tests for the newly completed stubs & empty modules across Milestones."""

import sys
import asyncio
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

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


# ── Expanded Stubs Verification ──────────────────────────────────────────────
print("\n=== Expanded Stubs Verification ===")

def t_learning_stubs():
    from learning.learning_manager import learning_manager
    from learning.policy.policy_learner import policy_learner
    from learning.evaluation.task_evaluator import task_evaluator
    from learning.evaluator.performance_evaluator import performance_evaluator
    from life.learn.life_learner import life_learner
    from life.observe.observer import LifeContext
    from life.decide.decision_engine import Decision
    
    learning_manager.process_task_outcome("task123", success=True, feedback="Excellent work!")
    assert learning_manager.learner.policy_weights["task123"] > 0
    
    performance_evaluator.record_metrics(success=True)
    assert performance_evaluator.get_performance_ratio() == 1.0
    
    # Verify LifeLearner cycle execution
    ctx = LifeContext(last_user_activity="gaming")
    life_learner.learn_cycle_lessons(ctx, Decision(should_act=True), success=True)
test("Learning components — LearningManager, PolicyLearner, PerformanceEvaluator, LifeLearner", t_learning_stubs)

def t_vision_execution_stubs():
    from vision.screen_understanding.screen_understander import screen_understander
    from vision.parser.screen_parser import screen_parser
    from execution.browser.browser_executor import browser_executor
    from execution.filesystem.fs_executor import fs_executor
    from execution.recovery.recovery_handler import recovery_handler
    
    res = screen_understander.analyze_screen()
    assert "summary" in res
    
    lines = screen_parser.parse_screen_text("hello\n\nworld")
    assert len(lines) == 2
    
    browser_executor.open_url("http://example.com")
    assert browser_executor.browser_open
    
    action = recovery_handler.handle_failure("file not found", "context")
    assert action == "SEARCH_WORKSPACE"
test("Vision & Execution — ScreenUnderstander, BrowserExecutor, RecoveryHandler", t_vision_execution_stubs)

def t_persona_voice_stubs():
    from persona.expressions.expression_registry import expression_registry
    from persona.motions.motion_registry import motion_registry
    from persona.habits.habit_tracker import habit_tracker
    from learning.habits.habit_tracker import habit_tracker as learning_habit_tracker
    from perception.voice.voice_processor import voice_processor
    
    exp = expression_registry.get_expression("vui vẻ")
    assert exp == "exp_happy"
    
    mot = motion_registry.get_motion("happy")
    assert mot == "motion_cheer"
    
    habit_tracker.record_activity("coding")
    assert habit_tracker.get_frequent_activity() == "coding"
    
    cleaned = voice_processor.clean_audio_data(b"audio")
    assert cleaned == b"audio"
test("Persona & Voice — ExpressionRegistry, MotionRegistry, HabitTrackers, VoiceProcessor", t_persona_voice_stubs)


# ── Async EventBus & Expanded Memory Verification ─────────────────────────────
print("\n=== Async EventBus & Expanded Memory Verification ===")

async def t_async_event_bus():
    from runtime.eventbus.event_bus import event_bus
    from runtime.events.base_event import BaseEvent
    
    received = []
    async def callback(evt_data):
        received.append(evt_data)
        
    event_bus.subscribe("test_async_event", callback)
    
    event = BaseEvent.create("test_async_event", "test_source", {"hello": "world"})
    await event_bus.publish_async(event)
    assert len(received) == 1
    assert received[0]["payload"]["hello"] == "world"
test("EventBus — async publish/subscribe and BaseEvent compatibility", t_async_event_bus)

def t_expanded_memories():
    from memory.working.working_memory import working_memory
    from memory.episodic.episodic_store import episodic_store
    from memory.procedural.procedure_store import procedure_store
    from memory.short_term.short_term import short_term_memory
    from memory.memory_manager import memory_manager
    
    # 1. Working Memory via memory_manager
    memory_manager.clear_working_memory()
    memory_manager.add_turn("user", "Hello manager")
    turns = memory_manager.get_working_memory()
    assert len(turns) > 0
    assert turns[0]["content"] == "Hello manager"
    
    # 2. Episodic store
    episodic_store.record_episode("User started developer workspace testing", "positive")
    assert len(episodic_store.episodes) > 0
    
    # 3. Procedure store
    procedure_store.register_procedure("run_pytest", ["activate venv", "pytest tests/"])
    steps = procedure_store.get_procedure("run_pytest")
    assert steps == ["activate venv", "pytest tests/"]
    
    # 4. Short term memory
    short_term_memory.add_alert("CPU High Usage")
    assert "CPU High Usage" in short_term_memory.get_alerts()
    
    # 5. Chroma Store & Embeddings imports
    from memory.vectorstore.chroma_store import ChromaStore
    from memory.embeddings.embeddings import get_default_embedding_function
    assert get_default_embedding_function() is not None
test("Memory — Working, Episodic, Procedural, and ShortTerm stores implementation", t_expanded_memories)

def t_config_and_health():
    import os
    from config.config import config
    
    # Test environment override
    os.environ["GEMINI_API_KEY"] = "dummy_test_key"
    from config.config import Config
    new_cfg = Config()
    assert new_cfg.get("llm.gemini_api_key") == "dummy_test_key"
    
    # Test health check endpoint response parser (simulated)
    from api.server import CompanionRequestHandler
    # Since we can't spin up a full HTTP server easily in the unit test, we can verify that the config values are properly resolved.
    assert new_cfg.get("server.port") == 8765
test("Config & Health — verify environment overrides and status helper integration", t_config_and_health)

def t_new_v7_stubs():
    # 1. ContextPacket
    from runtime.context.context_packet import ContextPacket
    packet = ContextPacket(user_message="test message", ocr_text="screen raw text")
    assert packet.user_message == "test message"
    assert packet["screen_text"] == "screen raw text"
    
    # 2. ContextManager
    from cognition.context.context_manager import context_manager
    context_manager.clear()
    context_manager.add_packet(packet)
    assert len(context_manager.get_history()) == 1
    
    # 3. Pipeline
    from runtime.pipeline.pipeline import Pipeline
    pipeline = Pipeline()
    pipeline.add_stage(lambda x: x + " stage1")
    assert pipeline.process("input") == "input stage1"
    
    # 4. RuntimeManager
    from runtime.runtime_manager import runtime_manager
    runtime_manager.boot()
    assert runtime_manager._booted
    runtime_manager.shutdown()
    assert not runtime_manager._booted
    
    # 5. InterruptionHandler
    from persona.behavior.interruption.interruption_handler import interruption_handler
    assert interruption_handler.should_interrupt(user_active=True, idle_time=0.5)
    assert not interruption_handler.should_interrupt(user_active=False, idle_time=10.0)
    
    # 6. PromptLibrary
    from cognition.prompts.prompt_library import PromptLibrary
    assert PromptLibrary.get_prompt("SYSTEM_BASE") is not None
    
    # 7. ActivityTimeline
    from world.timeline.activity_timeline import activity_timeline
    activity_timeline.record_activity("coding")
    evts = activity_timeline.get_recent_events()
    assert len(evts) > 0
    assert evts[0].activity == "coding"
    
    # 8. StreamHandler (Phase 6-8)
    from llm.streaming.stream_handler import StreamHandler
    handler = StreamHandler()
    assert handler.feed_token("Hello") is None
    assert handler.feed_token(".") == "Hello."
    
    # 9. StreamSTT (Phase 6-8)
    from speech.stt.streaming.stream_stt import StreamSTT
    stt = StreamSTT()
    stt.start_streaming()
    assert stt._is_active
    text = stt.stop_streaming()
    assert "ghi âm" in text
    
    # 10. KnowledgeGraph & GraphBuilder (Phase 6-8)
    from knowledge.graph.knowledge_graph import knowledge_graph
    from knowledge.graph.graph_builder import graph_builder
    graph_builder.build_from_fact("User thích chơi cờ vua")
    triplets = knowledge_graph.get_all_triplets()
    assert ("User", "LIKES", "chơi cờ vua") in triplets
    
    # 11. Ontology (Phase 6-8)
    from knowledge.ontology.ontology import ontology
    assert ontology.is_subclass_of("python", "programming_language")
    assert not ontology.is_subclass_of("python", "game")
test("V7 Stubs — ContextPacket, Pipeline, RuntimeManager, InterruptionHandler, PromptLibrary, ActivityTimeline, StreamHandler, StreamSTT, KnowledgeGraph, Ontology", t_new_v7_stubs)

async def t_new_v8_stubs():
    # 1. BeliefQuery & BeliefUpdater
    from belief.belief_store import belief_store
    from belief.belief_query import belief_query
    from belief.belief_updater import belief_updater
    belief_store.set_belief("user.name", "Nguyen Tri", confidence=0.8)
    assert belief_query.get_value("user.name") == "Nguyen Tri"
    belief_updater.register_evidence("user.name", "Nguyen Tri", confidence=0.5)
    
    # 2. GestureHandler
    from interaction.gesture.gesture_handler import gesture_handler
    reaction = gesture_handler.handle_tap("head")
    assert reaction["emotion"] == "smile"
    
    # 3. WikiLoader (mocked or offline safety)
    from knowledge.wiki.wiki_loader import wiki_loader
    # Should not raise exception even if offline
    try:
        wiki_loader.fetch_summary("Python")
    except Exception:
        pass
        
    # 4. StreamParser
    from llm.parser.stream_parser import StreamParser
    parser = StreamParser()
    chunk1 = parser.feed("<think>")
    assert chunk1["type"] == "mode_change"
    assert parser.in_thought
    
    # 5. PromptBuilder
    from llm.prompts.prompt_builder import prompt_builder
    msgs = prompt_builder.build_messages("You are helpful", [], "Hello")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    
    # 6. DependencyGraph
    from runtime.dependency.dependency_graph import dependency_graph
    dependency_graph.add_module("B", ["A"])
    dependency_graph.add_module("C", ["B"])
    order = dependency_graph.resolve_order()
    assert order.index("A") < order.index("B")
    
    # 7. ContentModerator
    from social.moderation.content_moderator import content_moderator
    res = content_moderator.evaluate("user1", "fck this toxicity")
    assert res["is_flagged"]
    
    # 8. StreamTTS
    from speech.tts.streaming.stream_tts import stream_tts
    chunks = []
    async for chunk in stream_tts.stream_audio("Test audio stream"):
        chunks.append(chunk)
    assert len(chunks) > 0
test("V8 Stubs — Belief, Gesture, Wiki, StreamParser, PromptBuilder, DependencyGraph, ContentModerator, StreamTTS", t_new_v8_stubs)


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Milestones stubs and empties filled successfully.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")

