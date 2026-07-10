"""Integration tests for Multi-Agent coordination and routing."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from agents.registry.agent_registry import agent_registry
from agents.coordinator.agent_coordinator import agent_coordinator


def test_agent_registry_completeness() -> None:
    """Verify that all core agents are registered with expected capabilities."""
    expected_agents = ["desktop", "browser", "coding", "memory", "research", "workspace"]
    for agent_name in expected_agents:
        # Check that agent can be found by at least one of its capabilities
        caps = agent_registry.list_all_agents()
        assert agent_name in caps
        assert len(caps[agent_name]) > 0


@pytest.mark.anyio
async def test_coordinator_route_task_to_workspace() -> None:
    """Verify task routing to WorkspaceAgent works correctly via AgentCoordinator."""
    # 1. Test routing project_context
    res_context = await agent_coordinator.route_task(
        capability="project_context",
        task_text="Check project context for current directory"
    )
    assert res_context["success"] is True
    assert "result" in res_context
    assert isinstance(res_context["result"], dict)

    # 2. Test routing workspace_snapshot
    res_snapshot = await agent_coordinator.route_task(
        capability="workspace_snapshot",
        task_text="Take a workspace snapshot"
    )
    assert res_snapshot["success"] is True
    assert "result" in res_snapshot
    inner_res = res_snapshot["result"]["result"]
    assert "files" in inner_res or "root" in inner_res or "project" in inner_res


@pytest.mark.anyio
async def test_coordinator_route_task_to_research() -> None:
    """Verify task routing to ResearchAgent works via AgentCoordinator."""
    from agents.research.research_agent import research_agent
    
    # Mock research_agent execute_task
    original_execute = research_agent.execute_task
    
    async def mock_execute_task(capability, payload):
        return {
            "success": True, 
            "report": "### Mocked Research Report\nResearch content description."
        }
        
    research_agent.execute_task = mock_execute_task
    
    try:
        res = await agent_coordinator.route_task(
            capability="research_web",
            task_text="Research details about WebGPU standard"
        )
        assert res["success"] is True
        assert "result" in res
        assert "report" in res["result"]
        assert "Mocked Research Report" in res["result"]["report"]
        
    finally:
        research_agent.execute_task = original_execute


@pytest.mark.anyio
async def test_coordinator_execute_parallel_workflow() -> None:
    """Verify coordinating parallel subtasks runs parallel execution successfully."""
    subtasks = [
        {"task": "Analyze codebase index.html", "focus_files": ["index.html"]},
        {"task": "Analyze styles.css", "focus_files": ["styles.css"]}
    ]
    
    # Mock run_parallel_subagents helper in subagent_service
    import agents.subagent_service as sas
    original_run_parallel = sas.run_parallel_subagents
    sas.run_parallel_subagents = AsyncMock(return_value=[
        {"success": True, "summary": "Done index.html analysis"},
        {"success": True, "summary": "Done styles.css analysis"}
    ])
    
    try:
        results = await agent_coordinator.execute_parallel_workflow(subtasks)
        assert len(results) == 2
        assert results[0]["success"] is True
        assert "index.html" in results[0]["summary"]
        assert results[1]["success"] is True
        assert "styles.css" in results[1]["summary"]
        
    finally:
        sas.run_parallel_subagents = original_run_parallel
