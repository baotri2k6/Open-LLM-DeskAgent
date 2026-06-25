import asyncio
import sys
import base64
import io
from pathlib import Path
from PIL import Image

# Add python-services directory to path
sys.path.append(str(Path(__file__).resolve().parents[1] / "python-services"))

from services.llm_service import _get_llm_credentials, _gemini_chat_with_tools, _openai_chat_with_tools
from core.config import config

async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== Testing VLM GUI Grounding (Mock Screenshot) ===")
    
    # 1. Create a dummy image representing a 1920x1080 screen
    dummy_img = Image.new("RGB", (1920, 1080), color="blue")
    buffered = io.BytesIO()
    dummy_img.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    provider, api_key, model, base_url = _get_llm_credentials()
    vlm_provider = provider
    vlm_model = model
    vlm_api_key = api_key
    vlm_base_url = base_url
    
    # Fallback to gemini if local ollama
    if provider == "ollama":
        gemini_key = config.get("llm.gemini_api_key")
        if gemini_key:
            vlm_provider = "gemini"
            vlm_model = "gemini-2.5-flash"
            vlm_api_key = gemini_key
        else:
            print("Gemini key is missing. Cannot call VLM.")
            return

    description = "nút Start ở góc dưới bên trái"
    prompt = (
        f"Bạn là một mô hình phân tích GUI thông minh.\n"
        f"Hãy phân tích ảnh chụp màn hình này và tìm vị trí chính xác của phần tử được mô tả: \"{description}\".\n"
        f"Hãy trả về kết quả dưới dạng JSON duy nhất có định dạng:\n"
        f'{{"x": <tọa độ X từ 0 đến 1000>, "y": <tọa độ Y từ 0 đến 1000>}}\n'
        f"Chú ý: 0,0 là góc trên bên trái, 1000,1000 là góc dưới bên phải màn hình. "
        f"Chỉ trả về đúng khối JSON, không viết lời giải thích nào khác."
    )
    
    print(f"Calling VLM API ({vlm_provider}/{vlm_model})...")
    
    try:
        if vlm_provider == "gemini":
            contents = [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": img_b64
                            }
                        }
                    ]
                }
            ]
            res = _gemini_chat_with_tools(contents, None, vlm_api_key, vlm_model)
            text_resp = res["candidates"][0]["content"]["parts"][0]["text"]
        else:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                    ]
                }
            ]
            res = _openai_chat_with_tools(messages, vlm_api_key, vlm_model, vlm_base_url)
            text_resp = res["choices"][0]["message"]["content"]
            
        print(f"VLM response: {text_resp}")
        
        # Verify JSON parsing
        import re
        import json
        m = re.search(r"(\{[\s\S]*?\})", text_resp)
        if m:
            coord = json.loads(m.group(1).strip())
            x_norm = float(coord.get("x", 500))
            y_norm = float(coord.get("y", 500))
            
            real_x = int((x_norm / 1000.0) * 1920)
            real_y = int((y_norm / 1000.0) * 1080)
            
            print(f"Normalized coords: ({x_norm}, {y_norm})")
            print(f"Translated physical coords: ({real_x}, {real_y})")
            print("Success! Coordinate parsing and translation work perfectly.")
        else:
            print("Failed to parse JSON coordinates.")
    except Exception as e:
        print(f"Error calling VLM: {e}")

if __name__ == "__main__":
    asyncio.run(main())
