"""Unit tests for CodingAgent and PlannerAgent integration."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.coding.coding_agent import CodingAgent, _extract_code_blocks
from agents.planner.planner_agent import PlannerAgent


def test_extract_code_blocks():
    text = """
    Here is the code fix:
    ```python
    # file: test_file.py
    def test_func():
        return 42
    ```
    And some other description.
    """
    blocks = _extract_code_blocks(text)
    assert len(blocks) == 1
    assert blocks[0][0] == "test_file.py"
    assert "def test_func():" in blocks[0][1]


def test_planner_detects_coding_task():
    planner = PlannerAgent()
    intent = planner.detect_intent("sửa code của file main.ts giúp mình")
    assert intent["name"] == "coding_task"
    assert "main.ts" in intent["task"]


@pytest.mark.anyio
async def test_planner_executes_coding_task():
    planner = PlannerAgent()
    
    # Mock run_coding_task
    with patch("agents.coding.coding_agent.run_coding_task", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {
            "success": True,
            "summary": "Đã sửa thành công lỗi lipsync",
            "files_changed": ["live2d-manager.js"]
        }
        
        res = await planner.handle_message("sửa lỗi code lipsync trong live2d-manager.js")
        
        mock_run.assert_called_once_with("sửa lỗi code lipsync trong live2d-manager.js")
        assert res["emotion"] == "excited"
        assert "hoàn thành sửa code" in res["text"]
