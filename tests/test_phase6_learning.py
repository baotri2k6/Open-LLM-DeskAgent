"""Phase 6 Integration Tests — kiểm tra Skill Extraction, Distillation, Knowledge và Experience Replay."""

import os
import sys
import shutil
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


# Dọn dẹp skill thử nghiệm sau khi test xong
SKILL_TEST_NAME = "test_distilled_git"


def cleanup():
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


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Phase 6 Learning & Distillation verified successfully.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")
