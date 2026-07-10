import pytest
import re
from unittest.mock import MagicMock, patch
from skills.skills_manager import SkillsManager
from llm.manager import LLMService


@pytest.mark.anyio
async def test_skills_manager_and_dynamic_injection():
    # 1. Test read_skill alias
    sm = SkillsManager()
    with patch.object(sm, "read_skill_content", return_value={"success": True, "content": "Skill Content"}) as mock_read:
        res = sm.read_skill("some_skill")
        mock_read.assert_called_once_with("some_skill")
        assert res["success"] is True
        assert res["content"] == "Skill Content"

    # 2. Test LLMService dynamic skill injection
    mock_skills = [
        {"name": "git-deploy", "description": "Auto deployment via git push"},
        {"name": "python-lint", "description": "Linter for python files"}
    ]
    
    with patch.object(sm, "list_skills", return_value=mock_skills), \
         patch.object(sm, "read_skill_content", return_value={"success": True, "content": "Git instructions"}):
         
        llm = LLMService()
        llm._skills_manager = sm
        
        # Test query that matches "git-deploy"
        async def mock_run_loop(*args, **kwargs):
            if False:
                yield None

        with patch.object(llm, "_run_agent_loop", side_effect=mock_run_loop) as mock_agent_loop:
            async for _ in llm.chat_stream("I want to do a git push deployment"):
                pass
            
            assert mock_agent_loop.called
            called_messages = mock_agent_loop.call_args[0][0]
            
            # Verify git-deploy detail was injected
            detail_messages = [m for m in called_messages if m["role"] == "system" and "CHI TIẾT HƯỚNG DẪN KỸ NĂNG: git-deploy" in m["content"]]
            assert len(detail_messages) == 1
            assert "Git instructions" in detail_messages[0]["content"]

            # Verify python-lint detail was NOT injected since the query had no match
            py_messages = [m for m in called_messages if m["role"] == "system" and "CHI TIẾT HƯỚNG DẪN KỸ NĂNG: python-lint" in m["content"]]
            assert len(py_messages) == 0
