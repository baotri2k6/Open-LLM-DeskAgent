"""Phase 6 Integration Tests — kiểm tra Skill Extraction, Distillation, Knowledge và Experience Replay."""

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


# Dọn dẹp skill thử nghiệm sau khi test xong
SKILL_TEST_NAME = "test_distilled_git"


def cleanup():
    import shutil
    from config.config import PROJECT_ROOT
    test_skill_dir = PROJECT_ROOT / "skills" / SKILL_TEST_NAME
    if test_skill_dir.exists():
        shutil.rmtree(test_skill_dir)


print("\n=== Phase 6: Skill Extraction & Distillation ===")

def t_skill_extractor():
    from planning.task_graph.task_graph import TaskGraph
    from learning.skill_extraction.skill_extractor import skill_extractor
    
    graph = TaskGraph("test_goal_1")
    graph.add_task("task_init", "Run init command")
    graph.add_task("task_write", "Write standard template")
    
    # Thiết lập thuộc tính bổ sung để giả lập cuộc gọi tool
    t1 = graph._tasks["task_init"]
    t1.tool_name = "execute_command"
    t1.arguments = {"command": "git init"}
    t1.status = "COMPLETED"
    
    t2 = graph._tasks["task_write"]
    t2.tool_name = "write_to_file"
    t2.arguments = {"path": "README.md", "content": "# Hello"}
    t2.status = "COMPLETED"
    
    recipe = skill_extractor.extract_recipe(graph)
    assert len(recipe) == 2
    assert recipe[0]["tool_name"] == "execute_command"
    assert recipe[1]["tool_name"] == "write_to_file"
test("SkillExtractor — extract steps from completed TaskGraph", t_skill_extractor)

def t_skill_distiller():
    from learning.distillation.skill_distiller import skill_distiller
    
    recipe = [
        {"tool_name": "execute_command", "arguments": {"command": "git add ."}},
        {"tool_name": "execute_command", "arguments": {"command": "git commit -m 'save'"}}
    ]
    
    cleanup()
    try:
        res = skill_distiller.distill_to_skill(
            skill_name=SKILL_TEST_NAME,
            description="Tự động hóa git add và commit",
            recipe=recipe
        )
        assert res["success"]
        
        # Verify file exists
        from config.config import PROJECT_ROOT
        skill_file = PROJECT_ROOT / "skills" / SKILL_TEST_NAME / "SKILL.md"
        assert skill_file.exists()
        
        content = skill_file.read_text(encoding="utf-8")
        assert "git add" in content
        assert "git commit" in content
    finally:
        cleanup()
test("SkillDistiller — distill recipe and save via SkillsManager", t_skill_distiller)


print("\n=== Phase 6: Knowledge & Experience Replay ===")

def t_knowledge_extractor():
    from learning.knowledge.knowledge_extractor import knowledge_extractor
    from belief.belief_store import belief_store
    
    # 1. Test trích xuất Editor
    res1 = knowledge_extractor.extract_from_text("Tớ thích dùng vscode để code hàng ngày.")
    assert "user.preference.editor" in res1
    assert res1["user.preference.editor"] == "vscode"
    assert belief_store.get_belief("user.preference.editor").value == "vscode"
    
    # 2. Test trích xuất Theme
    res2 = knowledge_extractor.extract_from_text("Tớ yêu thích giao diện dark mode màu đen.")
    assert "user.preference.theme" in res2
    assert "dark mode" in res2["user.preference.theme"].lower()
    
    # 3. Test trích xuất đặc điểm Night Owl
    res3 = knowledge_extractor.extract_from_text("Tớ thường xuyên code muộn ban đêm.")
    assert "user.trait.night_owl" in res3
    assert res3["user.trait.night_owl"] == "true"
test("KnowledgeExtractor — extract preferences and updates BeliefStore", t_knowledge_extractor)

def t_experience_replay():
    from learning.experience.experience_store import experience_store
    from learning.replay.experience_replay import experience_replay
    
    # Giả lập ghi nhận lỗi
    experience_store.record_experience(
        goal_id="g_fail",
        goal_desc="Build project on Windows",
        is_successful=False,
        lessons_learned="Task failed because of permission denied executing build.bat"
    )
    
    reports = experience_replay.replay_failures()
    assert len(reports) >= 1
    
    # Tìm report vừa tạo
    rep = [r for r in reports if r["goal_id"] == "g_fail"][0]
    assert "permission" in rep["lessons"].lower()
    assert "Yêu cầu phân quyền" in rep["recommendation"]
test("ExperienceReplay — analyze failure logs and generate recommendations", t_experience_replay)

def t_knowledge_distiller():
    from pathlib import Path
    import tempfile
    from learning.experience.experience_store import Experience
    from learning.distillation.knowledge_distiller import KnowledgeDistiller

    with tempfile.TemporaryDirectory() as tmpdir:
        distiller = KnowledgeDistiller(facts_path=Path(tmpdir) / "facts.json")
        experiences = [
            Experience(
                goal_id="g_perm",
                goal_desc="Build project on Windows",
                is_successful=False,
                lessons_learned="Task failed because permission denied while running build script.",
                metadata={"tool": "terminal_executor"},
            ),
            Experience(
                goal_id="g_net",
                goal_desc="Use memory vector store",
                is_successful=False,
                lessons_learned="ChromaDB embedding failed because network offline.",
            ),
        ]
        facts = distiller.distill_from_experiences(experiences)
        keys = {fact.key for fact in facts}
        assert "system.permission" in keys
        assert "system.network" in keys
        assert "tool.terminal_executor" in keys
        prompt_block = distiller.describe_for_prompt()
        assert "[Distilled Knowledge]" in prompt_block
        assert "permission" in prompt_block.lower()
test("KnowledgeDistiller — distill facts from ExperienceStore-style records", t_knowledge_distiller)

def t_pattern_learner():
    from pathlib import Path
    import tempfile
    import time
    from learning.patterns.pattern_learner import PatternLearner

    with tempfile.TemporaryDirectory() as tmpdir:
        learner = PatternLearner(patterns_path=Path(tmpdir) / "patterns.json")
        ts = time.mktime((2026, 6, 30, 22, 0, 0, 0, 0, -1))
        learner.record_event(activity="coding", tool="terminal_executor", timestamp=ts)
        learner.record_event(activity="testing", tool="pytest", timestamp=ts)
        learner.record_event(activity="coding", tool="terminal_executor", timestamp=ts)
        learner.record_event(activity="testing", tool="pytest", timestamp=ts)

        pred = learner.predict_next(current_activity="coding", hour=22)
        assert pred.activity == "testing"
        assert pred.tool in {"terminal_executor", "pytest"}
        assert pred.confidence > 0

        learner2 = PatternLearner(patterns_path=Path(tmpdir) / "patterns.json")
        assert learner2.predict_next(current_activity="coding", hour=22).activity == "testing"
        assert "[Predicted User Patterns]" in learner2.describe_for_prompt()
test("PatternLearner — learn time/tool patterns and predict next behavior", t_pattern_learner)

def t_prompt_includes_learning_blocks():
    from pathlib import Path
    import tempfile
    import importlib
    pb_mod = importlib.import_module("cognition.prompts.prompt_builder")
    from learning.distillation.knowledge_distiller import KnowledgeDistiller
    from learning.patterns.pattern_learner import PatternLearner

    with tempfile.TemporaryDirectory() as tmpdir:
        distiller = KnowledgeDistiller(facts_path=Path(tmpdir) / "facts.json")
        distiller._upsert_fact(
            "system.permission",
            "Ask for approval when permission errors happen.",
            "system",
            success=False,
        )
        distiller.save()

        learner = PatternLearner(patterns_path=Path(tmpdir) / "patterns.json")
        learner.record_event(activity="coding", tool="pytest")

        # Patch imported singletons through their source modules.
        kd_mod = importlib.import_module("learning.distillation.knowledge_distiller")
        pl_mod = importlib.import_module("learning.patterns.pattern_learner")
        old_kd = kd_mod.knowledge_distiller
        old_pl = pl_mod.pattern_learner
        kd_mod.knowledge_distiller = distiller
        pl_mod.pattern_learner = learner
        try:
            prompt = pb_mod.PromptBuilder().build(include_tools=False)
            assert "[Distilled Knowledge]" in prompt
            assert "[Predicted User Patterns]" in prompt
        finally:
            kd_mod.knowledge_distiller = old_kd
            pl_mod.pattern_learner = old_pl
test("PromptBuilder — inject distilled knowledge and learned patterns", t_prompt_includes_learning_blocks)


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Phase 6 Learning & Distillation verified successfully.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")
