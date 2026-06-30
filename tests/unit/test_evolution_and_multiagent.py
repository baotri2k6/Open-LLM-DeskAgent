"""Unit tests for Phase 8-9: PersistentIdentity, PersonalityEvolution, and ResearchAgent."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Import components
from persona.identity.persistent_identity import PersistentIdentity
from persona.identity.personality_evolution import PersonalityEvolution
from agents.research.research_agent import ResearchAgent
from agents.registry.agent_registry import AgentRegistry


def test_persistent_identity_basic_flow(tmp_path) -> None:
    # 1. Setup temporary file
    db_file = tmp_path / "test_identity.json"
    ident = PersistentIdentity(filepath=db_file)
    
    # 2. Check defaults
    assert ident.name == "IceGirl"
    assert ident.personality["friendly"] == 1.0
    
    # 3. Modify and save
    ident.name = "EvolvedIce"
    ident.update_trait("friendly", -0.2)
    ident.add_narrative_milestone("First milestone")
    ident.save()
    
    # 4. Reload and check persistence
    ident2 = PersistentIdentity(filepath=db_file)
    assert ident2.name == "EvolvedIce"
    assert ident2.personality["friendly"] == 0.8
    assert "First milestone" in ident2.self_narrative


def test_personality_evolution_sweep(tmp_path) -> None:
    # Setup files
    db_file = tmp_path / "test_identity_evolution.json"
    
    # Mock persistent_identity global reference
    import persona.identity.personality_evolution as pe_mod
    import persona.identity.persistent_identity as pi_mod
    
    test_ident = PersistentIdentity(filepath=db_file)
    original_pe_ident = pe_mod.persistent_identity
    original_pi_ident = pi_mod.persistent_identity
    
    pe_mod.persistent_identity = test_ident
    pi_mod.persistent_identity = test_ident
    
    # Mock Relationship Tracker
    import persona.relationship.relationship_tracker as rt_mod
    original_rt = rt_mod.relationship_tracker
    mock_rt = MagicMock()
    mock_rt.get_relationship_points.return_value = 200
    mock_rt.get_shared_experiences.return_value = 0
    mock_rt.level = "Người quen"
    rt_mod.relationship_tracker = mock_rt
    
    # Mock Belief Store
    import belief.belief_store as bs_mod
    original_bs = bs_mod.belief_store
    mock_bs = MagicMock()
    
    # Let's mock a belief structure
    class MockBelief:
        def __init__(self, key, value, confidence=0.8):
            self.key = key
            self.value = value
            self.confidence = confidence

    mock_bs.list_all_beliefs.return_value = [
        MockBelief("env.tool_broken.execute_command", "true"),
        MockBelief("user.likes.chess", "true")
    ]
    bs_mod.belief_store = mock_bs

    try:
        evo = PersonalityEvolution()
        evo.evolve_personality()
        
        # Friendly should increase from 1.0 -> clamped to 1.0
        # Shy should decrease from 0.3 -> 0.25
        assert test_ident.personality["shy"] == 0.25
        
        # Cautious trait should be created due to broken tool
        assert "cautious" in test_ident.personality
        assert test_ident.personality["cautious"] > 0.5
        
        # Chess should be added to favorite topics
        assert "Chess" in test_ident.favorite_topics
        assert any("Chess" in m for m in test_ident.self_narrative)
        
    finally:
        pe_mod.persistent_identity = original_pe_ident
        pi_mod.persistent_identity = original_pi_ident
        rt_mod.relationship_tracker = original_rt
        bs_mod.belief_store = original_bs


@pytest.mark.anyio
async def test_research_agent_capabilities() -> None:
    mock_llm = AsyncMock()
    mock_llm.chat.return_value = "### Test Report\nThis is a synthesized summary report."
    
    agent = ResearchAgent(llm_service=mock_llm)
    
    # 1. Test research_web
    import tools.browser_control as bc_mod
    original_search = bc_mod.search_google
    bc_mod.search_google = AsyncMock(return_value="search results snippet")
    
    try:
        res = await agent.execute_task("research_web", {"query": "deep learning"})
        assert res["success"] is True
        assert "Test Report" in res["report"]
        assert res["raw_data"] == "search results snippet"
        
        # 2. Test synthesize_report
        res_syn = await agent.execute_task("synthesize_report", {"snippets": ["snippet A", "snippet B"]})
        assert res_syn["success"] is True
        assert "Test Report" in res_syn["report"]
        
    finally:
        bc_mod.search_google = original_search


def test_agent_registry_research_registration() -> None:
    reg = AgentRegistry()
    # Find research agent
    research_agents = reg.find_agents_by_capability("research_web")
    assert "research" in research_agents
    
    # Check all capabilities
    all_caps = reg.get_all_capabilities()
    assert "research_web" in all_caps
    assert "literature_search" in all_caps


@pytest.mark.anyio
async def test_subagent_service_spawning() -> None:
    from agents.subagent_service import run_subagent, run_parallel_subagents
    from unittest.mock import patch, MagicMock

    mock_llm_service = MagicMock()
    
    async def mock_chat_stream(*args, **kwargs):
        yield "Chunk 1"
        yield {"type": "text", "text": " Chunk 2"}

    mock_llm_service.chat_stream = mock_chat_stream

    with patch("llm.manager.LLMService", return_value=mock_llm_service):
        # 1. Test single subagent execution
        res = await run_subagent(task="Write a python script", focus_files=["main.py"])
        assert res["success"] is True
        assert res["summary"] == "Chunk 1 Chunk 2"

        # 2. Test parallel subagents execution
        results = await run_parallel_subagents(
            tasks=["Task A", "Task B"],
            focus_files_list=[["a.py"], ["b.py"]]
        )
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[0]["summary"] == "Chunk 1 Chunk 2"
        assert results[1]["success"] is True
        assert results[1]["summary"] == "Chunk 1 Chunk 2"
