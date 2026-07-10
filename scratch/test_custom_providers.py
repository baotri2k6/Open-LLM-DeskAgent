import sys
from pathlib import Path
import os
import json

# Add python-services to sys.path
sys.path.append(str(Path(__file__).parent.parent / "python-services"))

# Force UTF-8 output for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from core.config import config
from services.llm_service import _get_llm_credentials, _is_multimodal_model, _to_gemini_format, _to_ollama_format
from agents.vision_agent import VisionAgent

def test_credentials_and_multimodal_checks():
    print("=== Testing Credentials & Multimodal Checks ===")
    
    # 1. Test Qwen provider credentials
    config.set("llm.provider", "qwen")
    config.set("llm.qwen_api_key", "test-qwen-key")
    config.set("llm.qwen_model", "qwen-vl-max")
    
    provider, api_key, model, base_url = _get_llm_credentials()
    assert provider == "qwen"
    assert api_key == "test-qwen-key"
    assert model == "qwen-vl-max"
    assert "dashscope.aliyuncs.com" in base_url
    print("[PASS] Qwen credentials loaded correctly.")
    
    # 2. Test DeepSeek provider credentials
    config.set("llm.provider", "deepseek")
    config.set("llm.deepseek_api_key", "test-deepseek-key")
    config.set("llm.deepseek_model", "deepseek-chat")
    
    provider, api_key, model, base_url = _get_llm_credentials()
    assert provider == "deepseek"
    assert api_key == "test-deepseek-key"
    assert model == "deepseek-chat"
    assert "api.deepseek.com" in base_url
    print("[PASS] DeepSeek credentials loaded correctly.")
    
    # 3. Test OpenAI compatible custom base url provider
    config.set("llm.provider", "openai-compatible")
    config.set("llm.openai_compatible_api_key", "test-custom-key")
    config.set("llm.openai_compatible_model", "local-llama3")
    config.set("llm.openai_compatible_base_url", "http://localhost:8000/v1")
    
    provider, api_key, model, base_url = _get_llm_credentials()
    assert provider == "openai-compatible"
    assert api_key == "test-custom-key"
    assert model == "local-llama3"
    assert base_url == "http://localhost:8000/v1"
    print("[PASS] OpenAI-Compatible Custom credentials loaded correctly.")
    
    # 4. Test multimodal check
    assert _is_multimodal_model("gemini", "gemini-2.5-flash") == True
    assert _is_multimodal_model("openai", "gpt-4o") == True
    assert _is_multimodal_model("openai", "gpt-3.5-turbo") == False
    assert _is_multimodal_model("qwen", "qwen-vl-plus") == True
    assert _is_multimodal_model("glm", "glm-4v") == True
    assert _is_multimodal_model("ollama", "llava:latest") == True
    assert _is_multimodal_model("ollama", "llama3") == False
    print("[PASS] Multimodal detection logic matches all target vision models.")

def test_multimodal_formatters():
    print("\n=== Testing Multimodal Formatters ===")
    
    base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this screen"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
        }
    ]
    
    # 1. Test Gemini format translation
    contents, sys_instr = _to_gemini_format(messages)
    assert len(contents) == 1
    parts = contents[0]["parts"]
    assert len(parts) == 2
    assert parts[0]["text"] == "Describe this screen"
    assert "inlineData" in parts[1]
    assert parts[1]["inlineData"]["mimeType"] == "image/png"
    assert parts[1]["inlineData"]["data"] == base64_image
    print("[PASS] Gemini multimodal formatter correctly extracted base64 image data.")
    
    # 2. Test Ollama format translation
    ollama_msgs = _to_ollama_format(messages)
    assert len(ollama_msgs) == 1
    assert ollama_msgs[0]["content"] == "Describe this screen"
    assert "images" in ollama_msgs[0]
    assert len(ollama_msgs[0]["images"]) == 1
    assert ollama_msgs[0]["images"][0] == base64_image
    print("[PASS] Ollama multimodal formatter successfully translated to Ollama images block.")

async def test_vision_agent_fallback():
    print("\n=== Testing Vision Agent Fallback ===")
    config.set("llm.provider", "ollama")
    config.set("llm.model", "qwen2.5:1.5b") # Text only model
    
    # Mock screen_reader functions to bypass headless environment failures
    import tools.screen_reader
    original_capture = tools.screen_reader.capture_screenshot
    original_ocr = tools.screen_reader.ocr_screenshot
    
    tools.screen_reader.capture_screenshot = lambda: {"success": True, "png_base64": "fake_base64", "size": (1920, 1080)}
    tools.screen_reader.ocr_screenshot = lambda: {"success": True, "text": "Hello from OCR screen text", "size": (1920, 1080)}
    
    try:
        agent = VisionAgent()
        res = await agent.describe_screen()
        print("Describe screen status:", res.get("success"))
        print("Output keys:", list(res.keys()))
        print("Message preview:", res.get("message"))
        assert res.get("success") == True # Should fall back to OCR successfully
        assert "OCR" in res.get("message")
        print("[PASS] VisionAgent correctly fell back to OCR for text-only model.")
    finally:
        # Restore original functions
        tools.screen_reader.capture_screenshot = original_capture
        tools.screen_reader.ocr_screenshot = original_ocr

if __name__ == "__main__":
    test_credentials_and_multimodal_checks()
    test_multimodal_formatters()
    
    import asyncio
    asyncio.run(test_vision_agent_fallback())
