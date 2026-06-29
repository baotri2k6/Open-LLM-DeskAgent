"""End-to-end integration test for Computer Use visual flow:
capture screenshot -> understand UI -> click element.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from tools.computer_control import click_element_by_vision


@pytest.mark.anyio
async def test_computer_use_end_to_end_flow() -> None:
    """Verify screenshot -> UI understanding -> coordinate grounding -> mouse click workflow."""
    
    # 1. Mock PyAutoGUI mouse functions to avoid physical interaction
    mock_pyautogui = MagicMock()
    
    # 2. Mock capture_screenshot to return dummy base64
    fake_screenshot = {
        "success": True,
        "png_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    }
    
    # 3. Mock LLM service replies for ScreenUnderstander and GroundingEngine
    # The first chat call is for screen understanding (JSON summary)
    # The second chat call is for VLM grounding (coordinates X, Y)
    mock_chat_responses = [
        # Screen understanding JSON response
        '{\n  "app_in_focus": "Web Browser",\n  "summary": "Login page showing username and password fields",\n  "interactive_elements": ["Sign In", "Username", "Password"]\n}',
        # Grounding coordinates response
        '180, 520'
    ]
    chat_call_index = 0
    
    def mock_chat_fn(prompt, context=None):
        nonlocal chat_call_index
        resp = mock_chat_responses[chat_call_index]
        chat_call_index += 1
        return resp

    # Patch modules
    with patch("pyautogui.moveTo") as mock_move, \
         patch("pyautogui.click") as mock_click, \
         patch("pyautogui.screenshot") as mock_shot, \
         patch("tools.screen_reader.capture_screenshot", return_value=fake_screenshot), \
         patch("llm.manager.llm_service.chat", side_effect=mock_chat_fn):
         
        # Execute the computer use visual click flow
        res = await click_element_by_vision(description="Nút Đăng nhập màu xanh", action_type="click")
        
        # Verify success
        assert res["success"] is True
        assert "coords" in res
        assert res["coords"] == {"x": 180, "y": 520}
        
        # Verify screen understanding context is captured in results
        assert "screen_analysis" in res
        assert res["screen_analysis"]["app_in_focus"] == "Web Browser"
        assert "Login page" in res["screen_analysis"]["summary"]
        
        # Verify mouse movement and click execution
        mock_move.assert_called_once_with(180, 520, duration=0.5)
        mock_click.assert_called_once()
