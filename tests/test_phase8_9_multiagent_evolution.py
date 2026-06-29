"""Phase 8 & 9 Integration Tests — kiểm tra Multi-Agent Ecosystem, Relationship Evolution & Persistent Identity."""

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


# ── Phase 8: Multi-Agent Ecosystem ───────────────────────────────────────────
print("\n=== Phase 8: Multi-Agent Ecosystem ===")

async def t_parallel_subagents():
    from agents.subagent_service import run_parallel_subagents
    tasks = [
        "Kiểm tra cấu hình môi trường phát triển",
        "Đọc tệp tin hướng dẫn đóng gói dự án"
    ]
    focus_files = [
        ["package.json"],
        ["README.md"]
    ]
    
    # Chạy song song các subagents
    results = await run_parallel_subagents(tasks, focus_files)
    assert len(results) == 2
    for res in results:
        assert "success" in res
test("SubagentService — run parallel subagents concurrently", t_parallel_subagents)

async def t_coordinator_parallel_workflow():
    from agents.coordinator.agent_coordinator import agent_coordinator
    subtasks = [
        {"task": "Phân tích file log lỗi", "focus_files": ["error.log"]},
        {"task": "Kiểm tra kết nối DB", "focus_files": ["config.py"]}
    ]
    
    results = await agent_coordinator.execute_parallel_workflow(subtasks)
    assert len(results) == 2
    for res in results:
        assert "success" in res
test("AgentCoordinator — execute parallel workflow coordination", t_coordinator_parallel_workflow)

async def t_research_agent_registered_and_synthesizes():
    from agents.registry.agent_registry import agent_registry

    assert "research" in agent_registry.find_agents_by_capability("synthesize_report")
    result = await agent_registry.route_task("synthesize_report", {
        "query": "DeskAgent companion roadmap",
        "sources": ["README.md", "COMPANION_ROADMAP.md"]
    })
    assert result["success"]
    assert result["agent"] == "research"
    assert result["result"]["source_count"] >= 1
    assert len(result["result"]["findings"]) >= 1
test("ResearchAgent — registered research synthesis capability", t_research_agent_registered_and_synthesizes)


# ── Phase 9: Companion Evolution & Persistent Identity ──────────────────────
print("\n=== Phase 9: Companion Evolution & Persistent Identity ===")

def t_multidimensional_relationship():
    from pathlib import Path
    import tempfile
    from persona.relationship.relationship_tracker import RelationshipTracker
    
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "test_user_profile.json"
        tracker = RelationshipTracker(profile_path=profile_path)
        
        # Mặc định là Người lạ
        assert tracker.level == "Người lạ"
        assert tracker.get_shared_experiences() == 0
        assert len(tracker.get_inside_jokes()) == 0
        
        # Thêm trải nghiệm chung và inside joke
        tracker.add_shared_experience()
        tracker.add_inside_joke("Cú đêm debug 3h sáng")
        
        # Tăng điểm quan hệ lên cấp Tri kỷ (> 800)
        tracker.add_raw(850)
        assert tracker.level == "Tri kỷ"
        assert "Unconditional trust" in tracker.perks
        
        # Lưu trữ thành công
        snapshot = tracker.snapshot()
        assert snapshot["score"] == 850
        assert snapshot["shared_experiences"] == 1
        assert "Cú đêm debug 3h sáng" in snapshot["inside_jokes"]
        
        # Load lại từ đĩa để kiểm chứng Persistent Identity
        tracker2 = RelationshipTracker(profile_path=profile_path)
        assert tracker2.score == 850
        assert tracker2.level == "Tri kỷ"
        assert tracker2.get_shared_experiences() == 1
        assert "Cú đêm debug 3h sáng" in tracker2.get_inside_jokes()
test("RelationshipTracker — Multi-dimensional metrics, inside jokes, and persistence", t_multidimensional_relationship)

def t_belief_store_serialization():
    from pathlib import Path
    import tempfile
    from belief.belief_store import BeliefStore
    
    with tempfile.TemporaryDirectory() as tmpdir:
        beliefs_path = Path(tmpdir) / "test_user_beliefs.json"
        store = BeliefStore(beliefs_path=beliefs_path)
        
        # Ghi nhận một niềm tin mới
        store.set_belief("user.preference.language", "vietnamese", confidence=0.9, source="direct_feedback")
        store.set_belief("user.trait.hardworking", "true", confidence=0.75, source="observation")
        
        # Khởi tạo store mới load từ đĩa
        store2 = BeliefStore(beliefs_path=beliefs_path)
        belief_lang = store2.get_belief("user.preference.language")
        belief_trait = store2.get_belief("user.trait.hardworking")
        
        assert belief_lang is not None
        assert belief_lang.value == "vietnamese"
        assert belief_lang.confidence == 0.9
        
        assert belief_trait is not None
        assert belief_trait.value == "true"
        assert belief_trait.confidence == 0.75
test("BeliefStore — Serialize and load back beliefs from JSON", t_belief_store_serialization)

def t_personality_evolution_and_persistent_identity():
    from pathlib import Path
    import tempfile
    from persona.identity.character_profile import CharacterProfile
    from persona.identity.persistent_identity import PersistentIdentity
    from persona.evolution.personality_evolution import PersonalityEvolution
    from persona.relationship.relationship_tracker import RelationshipTracker
    from belief.user_model import UserModel
    from belief.belief_store import BeliefStore

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        profile = CharacterProfile.default()
        identity_path = base / "identity.json"
        identity = PersistentIdentity(identity_path=identity_path)
        evolution = PersonalityEvolution(identity=identity)

        tracker = RelationshipTracker(profile_path=base / "user_profile.json")
        tracker.add_raw(850)
        tracker.add_shared_experience()
        tracker.add_shared_experience()
        tracker.add_shared_experience()

        belief_store = BeliefStore(beliefs_path=base / "beliefs.json")
        belief_store.set_belief("user.trait.night_owl", "true", confidence=0.9)
        belief_store.set_belief("user.preference.editor", "vscode", confidence=0.9)

        class LocalUserModel(UserModel):
            def get_preference(self, key: str, default: str = "") -> str:
                belief = belief_store.get_belief(f"user.preference.{key}")
                return belief.value if belief and belief.confidence > 0.4 else default

            def get_user_traits(self) -> list[str]:
                traits = []
                for belief in belief_store.list_all_beliefs():
                    if belief.key.startswith("user.trait.") and belief.value == "true" and belief.confidence > 0.6:
                        traits.append(belief.key.replace("user.trait.", ""))
                return traits

        result = evolution.evolve(profile, tracker, LocalUserModel())
        assert result.changed
        assert "supportive" in profile.speech_style
        assert "night owl hacks" in profile.favorite_topics
        assert "vscode tips" in profile.favorite_topics
        assert "shared project memories" in profile.favorite_topics

        identity2 = PersistentIdentity(identity_path=identity_path)
        assert "supportive" in identity2.snapshot.unlocked_styles
        assert "night owl hacks" in identity2.snapshot.favorite_topics
        assert identity2.snapshot.display_name == profile.name
test("PersonalityEvolution + PersistentIdentity — durable companion growth", t_personality_evolution_and_persistent_identity)


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Phase 8 & 9 stacks verified successfully.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")
