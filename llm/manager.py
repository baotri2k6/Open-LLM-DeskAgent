"""LLM facade — Ollama/Gemini/OpenAI api supporting OS Agent and local tool calling fallback."""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
import asyncio
import queue
import threading
import uuid
import re
from config.config import config
from runtime.logger import get_logger
from persona.dialogue.system_prompt import build_system_prompt
from persona.persona_manager import PersonaManager

# Import tools
from tools.computer_control import mouse_click, mouse_move, keyboard_type, keyboard_press, execute_command, click_element_by_vision, mouse_scroll, mouse_drag
from tools.file_writer import write_to_file
from tools.file_reader import read_file
from tools.browser_control import search_google, open_url
from tools.mxh_tools import search_twitter, read_reddit_post, get_youtube_transcript, search_bilibili, read_webpage_jina
from execution.approval.approval_registry import wait_for_approval
from plugins.plugin_manager import PluginManager
from skills.skills_manager import SkillsManager

logger = get_logger("ai-companion.llm")

OLLAMA_URL = "http://127.0.0.1:11434"


def _get_llm_credentials() -> tuple[str, str, str, str]:
    """Returns (provider, api_key, model, base_url)."""
    provider = config.get("llm.provider", "ollama")
    
    if provider == "gemini":
        api_key = config.get("llm.gemini_api_key") or os.getenv("GEMINI_API_KEY", "")
        model = config.get("llm.gemini_model", "gemini-2.5-flash")
        base_url = "https://generativelanguage.googleapis.com"
        
    elif provider == "openai":
        api_key = config.get("llm.openai_api_key") or os.getenv("OPENAI_API_KEY", "")
        model = config.get("llm.openai_model", "gpt-4o-mini")
        base_url = "https://api.openai.com/v1"
        
    elif provider == "deepseek":
        api_key = config.get("llm.deepseek_api_key") or os.getenv("DEEPSEEK_API_KEY", "")
        model = config.get("llm.deepseek_model", "deepseek-chat")
        base_url = config.get("llm.deepseek_base_url") or "https://api.deepseek.com/v1"
        
    elif provider == "glm":
        api_key = config.get("llm.glm_api_key") or os.getenv("GLM_API_KEY", "")
        model = config.get("llm.glm_model", "glm-4")
        base_url = config.get("llm.glm_base_url") or "https://open.bigmodel.cn/api/paas/v4"
        
    elif provider == "qwen":
        api_key = config.get("llm.qwen_api_key") or os.getenv("QWEN_API_KEY", "")
        model = config.get("llm.qwen_model", "qwen-plus")
        base_url = config.get("llm.qwen_base_url") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
    elif provider == "openai-compatible":
        api_key = config.get("llm.openai_compatible_api_key") or os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
        model = config.get("llm.openai_compatible_model", "")
        base_url = config.get("llm.openai_compatible_base_url", "")
        
    else: # ollama
        api_key = ""
        model = config.get("llm.model", "qwen2.5:1.5b")
        base_url = config.get("llm.host") or OLLAMA_URL
        
    return provider, api_key, model, base_url


def _is_multimodal_model(provider: str, model: str) -> bool:
    if provider == "gemini":
        return True
    if provider == "openai" and ("gpt-4o" in model or "gpt-4-vision" in model):
        return True
    model_lower = model.lower()
    if any(k in model_lower for k in ["vl", "vision", "multimodal", "-v", "glm-4v", "llava", "minicpm", "mllama"]):
        return True
    return False





async def execute_tool(name: str, args: dict, mcp_manager = None) -> dict:
    """Gọi thực thi tool tương ứng dựa trên tên và các đối số."""
    try:
        if name.startswith("mcp__"):
            if mcp_manager:
                return await mcp_manager.call_tool(name, args)
            else:
                return {"success": False, "error": "MCP Manager chưa được khởi tạo."}

        # Kiểm tra và thực thi Plugin tool
        plugin_mgr = PluginManager()
        if name in plugin_mgr.tools_registry:
            res = await plugin_mgr.execute_tool(name, args)
            if isinstance(res, dict):
                return res
            return {"success": True, "output": res}

        if name == "execute_command":
            return execute_command(args.get("command", ""))
        elif name == "write_to_file":
            return write_to_file(args.get("path", ""), args.get("content", ""), args.get("overwrite", True))
        elif name == "read_file":
            return read_file(args.get("path", ""))
        elif name == "mouse_click":
            return mouse_click(
                int(args.get("x", 0)), 
                int(args.get("y", 0)), 
                args.get("button", "left"), 
                args.get("double_click", False)
            )
        elif name == "mouse_move":
            return mouse_move(
                int(args.get("x", 0)), 
                int(args.get("y", 0))
            )
        elif name == "mouse_scroll":
            x_val = args.get("x")
            y_val = args.get("y")
            return mouse_scroll(
                int(args.get("clicks", 1)),
                args.get("direction", "down"),
                int(x_val) if x_val is not None else None,
                int(y_val) if y_val is not None else None
            )
        elif name == "mouse_drag":
            return mouse_drag(
                int(args.get("x", 0)),
                int(args.get("y", 0)),
                args.get("button", "left"),
                float(args.get("duration", 0.5))
            )
        elif name == "keyboard_type":
            return keyboard_type(args.get("text", ""))
        elif name == "keyboard_press":
            return keyboard_press(args.get("keys", ""))
        elif name == "open_application":
            from agents.desktop.desktop_agent import DesktopAgent
            agent = DesktopAgent()
            return await agent.open_application(args.get("app_name", ""))
        elif name == "open_url":
            from tools.browser_control import open_url
            return open_url(args.get("url", ""))
        elif name == "click_element_by_vision":
            return click_element_by_vision(args.get("description", ""), args.get("action_type", "click"))
        elif name == "search_google":
            return search_google(args.get("query", ""))
        elif name == "search_twitter":
            return search_twitter(args.get("query", ""), int(args.get("limit", 5)))
        elif name == "read_reddit_post":
            return read_reddit_post(args.get("subreddit", ""), int(args.get("limit", 5)))
        elif name == "get_youtube_transcript":
            return get_youtube_transcript(args.get("video_url", ""))
        elif name == "search_bilibili":
            return search_bilibili(args.get("query", ""), int(args.get("limit", 5)))
        elif name == "read_webpage_jina":
            return read_webpage_jina(args.get("url", ""))
        elif name == "spawn_subagent":
            from agents.subagent_service import run_subagent
            return await run_subagent(args.get("task", ""), args.get("focus_files"))
        elif name == "read_skill":
            return SkillsManager().read_skill_content(args.get("name", ""))
        elif name == "skill_manage":
            return SkillsManager().manage_skill(
                args.get("action", ""),
                args.get("name", ""),
                args.get("content", ""),
                args.get("description", "")
            )
        else:
            return {"success": False, "error": f"Không tìm thấy tool: {name}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _parse_json_fallback(text: str) -> dict | None:
    """Fallback phân tách cấu trúc JSON gọi tool từ câu trả lời dạng văn bản thô (cho Ollama)."""
    # Tìm khối code ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
            
    # Tìm cặp dấu ngoặc nhọn chứa tool hoặc action
    m = re.search(r"(\{[\s\S]*?\})", text)
    if m:
        try:
            val = json.loads(m.group(1).strip())
            if "tool" in val or "action" in val:
                return val
        except Exception:
            pass
    return None


OLLAMA_SYSTEM_INSTRUCTION = """
=== HƯỚNG DẪN GỌI CÔNG CỤ (SYSTEM TOOLS) ===
Bạn có quyền truy cập vào các công cụ điều khiển hệ thống. Nếu bạn cần thực hiện hành động trên máy tính của người dùng (như tạo file, chạy lệnh, tìm kiếm, v.v.), hãy trả về một KHỐI JSON duy nhất theo định dạng dưới đây và KHÔNG kèm theo lời giải thích nào khác ngoài khối JSON này:

{
  "tool": "tên_công_cụ",
  "args": {
    "tên_tham_số": "giá_trị"
  }
}

Các công cụ khả dụng bao gồm:
1. `execute_command` (args: `command`): Chạy lệnh shell (cmd/powershell).
2. `write_to_file` (args: `path`, `content`, `overwrite`): Viết file.
3. `read_file` (args: `path`): Đọc nội dung file.
4. `mouse_click` (args: `x`, `y`, `button`, `double_click`): Click chuột.
5. `mouse_move` (args: `x`, `y`): Rê chuột đến tọa độ.
6. `mouse_scroll` (args: `clicks`, `direction`, `x`, `y`): Cuộn màn hình lên hoặc xuống.
7. `mouse_drag` (args: `x`, `y`, `button`, `duration`): Kéo và thả chuột từ vị trí hiện tại đến tọa độ.
8. `keyboard_type` (args: `text`): Gõ phím.
9. `keyboard_press` (args: `keys`): Nhấn phím nóng.
10. `open_application` (args: `app_name`): Mở ứng dụng.
11. `search_google` (args: `query`): Tìm kiếm Google.
12. `search_twitter` (args: `query`, `limit`): Tìm kiếm bài đăng trên Twitter/X.
13. `read_reddit_post` (args: `subreddit`, `limit`): Đọc bài viết hot trên Reddit.
14. `get_youtube_transcript` (args: `video_url`): Tải phụ đề video YouTube.
15. `search_bilibili` (args: `query`, `limit`): Tìm video trên Bilibili.
16. `read_webpage_jina` (args: `url`): Đọc toàn bộ nội dung của trang web.
17. `open_url` (args: `url`): Mở một đường dẫn liên kết URL bằng trình duyệt mặc định của hệ thống.
18. `click_element_by_vision` (args: `description`, `action_type`): Sử dụng thị giác máy tính để tự động click, click đúp hoặc di chuột đến một phần tử màn hình dựa trên mô tả trực quan của nó.
19. `read_skill` (args: `name`): Đọc chi tiết toàn bộ hướng dẫn thực thi (SKILL.md) của một kỹ năng cụ thể.
20. `skill_manage` (args: `action`, `name`, `content`, `description`): Quản lý (tạo mới, cập nhật, xóa) các kỹ năng cục bộ.

Sau khi hệ thống trả về kết quả chạy của công cụ, bạn có thể phân tích kết quả đó để tiếp tục gọi công cụ khác hoặc đưa ra câu trả lời cuối cùng bằng ngôn ngữ tự nhiên thông thường.
"""

TOOLS_SCHEMA = [
    {
        "name": "execute_command",
        "description": "Chạy lệnh shell (cmd/powershell trên Windows).",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Lệnh cmd hoặc powershell cần thực thi."}
            },
            "required": ["command"]
        }
    },
    {
        "name": "write_to_file",
        "description": "Ghi nội dung vào một file trên máy tính.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Đường dẫn tới file cần tạo hoặc ghi đè."},
                "content": {"type": "string", "description": "Nội dung cần viết vào file."},
                "overwrite": {"type": "boolean", "description": "Có cho phép ghi đè nếu file đã tồn tại hay không."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "Đọc nội dung một file văn bản hoặc tài liệu.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Đường dẫn tới file."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "mouse_click",
        "description": "Click chuột tại tọa độ x, y trên màn hình.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Tọa độ X."},
                "y": {"type": "integer", "description": "Tọa độ Y."},
                "button": {"type": "string", "description": "Nút chuột: 'left' hoặc 'right'."},
                "double_click": {"type": "boolean", "description": "Có phải click đúp hay không."}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "mouse_move",
        "description": "Di chuyển con trỏ chuột đến tọa độ x, y.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Tọa độ X."},
                "y": {"type": "integer", "description": "Tọa độ Y."}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "mouse_scroll",
        "description": "Cuộn màn hình lên hoặc xuống.",
        "parameters": {
            "type": "object",
            "properties": {
                "clicks": {"type": "integer", "description": "Số nấc cuộn chuột (ví dụ: 3, 5, 10). Mặc định là 1."},
                "direction": {"type": "string", "enum": ["up", "down"], "description": "Hướng cuộn: 'up' (lên) hoặc 'down' (xuống). Mặc định là 'down'."},
                "x": {"type": "integer", "description": "Tọa độ X cần di chuyển chuột tới trước khi cuộn (tùy chọn)."},
                "y": {"type": "integer", "description": "Tọa độ Y cần di chuyển chuột tới trước khi cuộn (tùy chọn)."}
            },
            "required": ["clicks"]
        }
    },
    {
        "name": "mouse_drag",
        "description": "Kéo và thả chuột từ vị trí hiện tại đến tọa độ x, y.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Tọa độ X đích kéo thả chuột tới."},
                "y": {"type": "integer", "description": "Tọa độ Y đích kéo thả chuột tới."},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Phím nhấn giữ chuột: 'left' (trái), 'right' (phải), 'middle' (giữa). Mặc định là 'left'."},
                "duration": {"type": "number", "description": "Thời gian thực hiện hành động kéo rê chuột (tính bằng giây). Mặc định là 0.5."}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "keyboard_type",
        "description": "Gõ một chuỗi văn bản từ bàn phím.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Văn bản cần gõ."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "keyboard_press",
        "description": "Ấn một phím hoặc tổ hợp phím ảo.",
        "parameters": {
            "type": "object",
            "properties": {
                "keys": {"type": "string", "description": "Phím hoặc tổ hợp phím (ví dụ: 'enter', 'ctrl+c')."}
            },
            "required": ["keys"]
        }
    },
    {
        "name": "open_application",
        "description": "Mở một ứng dụng trên hệ điều hành.",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Tên ứng dụng cần mở."}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "open_url",
        "description": "Mở một đường dẫn liên kết URL (trang web, bài hát youtube, v.v.) bằng trình duyệt mặc định của hệ thống.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Địa chỉ URL cần mở (ví dụ: 'https://youtube.com')."}
            },
            "required": ["url"]
        }
    },
    {
        "name": "click_element_by_vision",
        "description": "Sử dụng thị giác máy tính (VLM) để định vị và tương tác chuột (click, click đúp, di chuột) vào một phần tử trên màn hình dựa trên mô tả trực quan của phần tử đó.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Mô tả trực quan của phần tử cần tương tác (ví dụ: 'Nút đăng nhập màu xanh', 'Biểu tượng Google Chrome trên màn hình')."},
                "action_type": {"type": "string", "enum": ["click", "double_click", "move"], "description": "Hành động mong muốn thực hiện (mặc định là 'click')."}
            },
            "required": ["description"]
        }
    },
    {
        "name": "search_google",
        "description": "Tìm kiếm google qua trình duyệt mặc định.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Từ khóa tìm kiếm."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_twitter",
        "description": "Tìm kiếm các thảo luận, tin tức gần đây trên Twitter/X.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Từ khóa tìm kiếm."},
                "limit": {"type": "integer", "description": "Số lượng bài đăng muốn lấy (mặc định 5)."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_reddit_post",
        "description": "Đọc các bài đăng hot nhất trên một Subreddit của Reddit.",
        "parameters": {
            "type": "object",
            "properties": {
                "subreddit": {"type": "string", "description": "Tên Subreddit (ví dụ: 'python', 'funny')."},
                "limit": {"type": "integer", "description": "Số lượng bài đăng muốn lấy (mặc định 5)."}
            },
            "required": ["subreddit"]
        }
    },
    {
        "name": "get_youtube_transcript",
        "description": "Tải transcript/phụ đề của một video YouTube.",
        "parameters": {
            "type": "object",
            "properties": {
                "video_url": {"type": "string", "description": "Đường dẫn URL của video YouTube."}
            },
            "required": ["video_url"]
        }
    },
    {
        "name": "search_bilibili",
        "description": "Tìm kiếm video và nội dung trên Bilibili.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Từ khóa tìm kiếm."},
                "limit": {"type": "integer", "description": "Số lượng kết quả (mặc định 5)."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_webpage_jina",
        "description": "Đọc nội dung đầy đủ của một trang web hoặc bài báo cụ thể bằng Jina Reader.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Đường dẫn URL của trang web cần đọc."}
            },
            "required": ["url"]
        }
    },
    {
        "name": "spawn_subagent",
        "description": "Ủy quyền một nhiệm vụ độc lập cho một subagent chạy ngầm với bộ nhớ (context) tách biệt. Dùng khi cần xử lý các tác vụ đọc nhiều file, nghiên cứu hoặc viết mã nguồn phức tạp để tránh làm tràn bộ nhớ chính.",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Nhiệm vụ cụ thể giao cho subagent (ví dụ: 'Hãy đọc file main.py và giải thích cấu trúc')."},
                "focus_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách các tệp tin subagent cần tập trung xử lý."
                }
            },
            "required": ["task"]
        }
    },
    {
        "name": "read_skill",
        "description": "Đọc chi tiết toàn bộ hướng dẫn thực thi (SKILL.md) của một kỹ năng hệ thống cụ thể.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Tên của kỹ năng muốn đọc (ví dụ: 'note-taking-obsidian')."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "skill_manage",
        "description": "Quản lý (tạo mới, cập nhật, xóa) các kỹ năng hệ thống cục bộ.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "update", "delete"],
                    "description": "Hành động muốn thực hiện: 'create' (tạo mới), 'update' (cập nhật nội dung), 'delete' (xóa kỹ năng)."
                },
                "name": {"type": "string", "description": "Tên kỹ năng (dùng chữ thường, phân tách bằng dấu gạch ngang, ví dụ: 'note-taking-obsidian')."},
                "content": {"type": "string", "description": "Nội dung hướng dẫn chi tiết của kỹ năng (không bắt buộc với action 'delete')."},
                "description": {"type": "string", "description": "Mô tả ngắn gọn về chức năng của kỹ năng (chỉ bắt buộc khi chọn action 'create')."}
            },
            "required": ["action", "name"]
        }
    }
]


def _capture_screen_b64() -> str | None:
    """Chụp ảnh màn hình hiện tại và mã hóa base64 để làm bối cảnh thị giác."""
    import pyautogui
    import io
    import base64
    from PIL import Image
    try:
        screenshot = pyautogui.screenshot()
        width, height = screenshot.size
        max_size = 1024
        if max(width, height) > max_size:
            screenshot.thumbnail((max_size, max_size))
        buffered = io.BytesIO()
        screenshot.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception:
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                width, height = screenshot.size
                max_size = 1024
                if max(width, height) > max_size:
                    screenshot.thumbnail((max_size, max_size))
                buffered = io.BytesIO()
                screenshot.save(buffered, format="PNG")
                return base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception:
            return None


class LLMService:
    _conversation_history: list[dict[str, str]] = []
    _mcp_manager = None
    _plugin_manager = None
    _skills_manager = None

    def __init__(self) -> None:
        self.persona_mgr = PersonaManager()
        self._persona = self.persona_mgr.load_persona("icegirl")
        self._system_prompt = self._build_system_prompt()
        
        # Tích hợp MCP dạng Singleton
        if LLMService._mcp_manager is None:
            try:
                from mcp_agent.server_registry import ServerRegistry
                from mcp_agent.mcp_client import MCPClientManager
                registry = ServerRegistry()
                LLMService._mcp_manager = MCPClientManager(registry)
            except Exception as e:
                logger.warning(f"MCP: Không thể khởi tạo hệ thống MCP: {e}")
                LLMService._mcp_manager = None

        # Tích hợp Plugin SDK dạng Singleton
        if LLMService._plugin_manager is None:
            try:
                LLMService._plugin_manager = PluginManager()
            except Exception as e:
                logger.warning(f"PluginManager: Không thể khởi tạo PluginManager: {e}")
                LLMService._plugin_manager = None

        # Tích hợp Skills Manager dạng Singleton
        if LLMService._skills_manager is None:
            try:
                LLMService._skills_manager = SkillsManager()
            except Exception as e:
                logger.warning(f"SkillsManager: Không thể khởi tạo SkillsManager: {e}")
                LLMService._skills_manager = None

    @property
    def mcp_manager(self):
        return LLMService._mcp_manager

    @property
    def plugin_manager(self):
        return LLMService._plugin_manager

    @property
    def skills_manager(self):
        return LLMService._skills_manager

    def _build_system_prompt(self, rel_level: str = "Người quen", mood: str = "vui vẻ", time_note: str = "", force_english: bool = False, activity: str = "unknown") -> str:
        avatar_model = config.get("app.avatarModel", "IceGirl")
        persona_name = "icegirl"
        if "hiyori" in avatar_model.lower():
            persona_name = "hiyori"
        elif "mao" in avatar_model.lower():
            persona_name = "mao"
        elif "huohuo" in avatar_model.lower():
            persona_name = "huohuo"
        
        self._persona = self.persona_mgr.load_persona(persona_name)
        return build_system_prompt(self._persona, rel_level, mood, time_note, force_english=force_english, activity=activity)

    @classmethod
    def _get_session_history(cls) -> list[dict[str, str]]:
        return cls._conversation_history

    @classmethod
    def _append_to_history(cls, role: str, content: str):
        cls._conversation_history.append({"role": role, "content": content})
        if len(cls._conversation_history) > 40:
            cls._conversation_history = cls._conversation_history[-40:]

    def _estimate_tokens(self, messages: list[dict]) -> int:
        total_chars = 0
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for part in content:
                    if part.get("type") == "text":
                        total_chars += len(part.get("text", ""))
            total_chars += 50
        return total_chars // 4

    async def _compact_context_if_needed(self, messages: list[dict], provider: str, api_key: str, model: str, base_url: str) -> list[dict]:
        estimated_tokens = self._estimate_tokens(messages)
        context_limit = config.get("llm.context_size") or 8192
        try:
            context_limit = int(context_limit)
        except Exception:
            context_limit = 8192
            
        threshold = int(context_limit * 0.8)
        
        if estimated_tokens > threshold and len(messages) > 5:
            logger.info("Context length %d exceeds threshold %d. Running auto-compaction...", estimated_tokens, threshold)
            
            summary_messages = [
                {"role": "system", "content": "Bạn là trợ lý hệ thống. Hãy viết một bản tóm tắt cực kỳ ngắn gọn (dưới 150 từ) về tiến trình cuộc hội thoại hiện tại. Tóm tắt bao gồm: những nhiệm vụ đã hoàn thành, lỗi gặp phải, và bước tiếp theo cần làm. Bản tóm tắt này sẽ được dùng làm bộ nhớ tiếp nối cho lượt hội thoại sau."},
                {"role": "user", "content": f"Lịch sử hội thoại cần tóm tắt:\n{json.dumps(messages[1:-1], ensure_ascii=False)}"}
            ]
            
            summary = ""
            try:
                provider_instance = None
                if provider == "gemini":
                    from llm.providers.gemini import GeminiProvider
                    provider_instance = GeminiProvider()
                elif provider in ["openai", "deepseek", "glm", "qwen", "openai-compatible"]:
                    from llm.providers.openai import OpenAIProvider
                    provider_instance = OpenAIProvider()
                else: # ollama
                    from llm.providers.ollama import OllamaProvider
                    provider_instance = OllamaProvider()
                
                res = provider_instance.chat_with_tools(summary_messages, api_key, model, base_url)
                summary = res.get("content", "") or "Không thể tạo tóm tắt do lỗi hệ thống."
            except Exception as e:
                logger.error("Failed to generate context compaction summary: %s", e)
                summary = "Không thể tạo tóm tắt do lỗi hệ thống."

            new_messages = []
            if messages and messages[0]["role"] == "system":
                new_messages.append(messages[0])
            
            new_messages.append({
                "role": "system",
                "content": f"=== TỐM TẮT TIẾN TRÌNH TRƯỚC ĐÓ (ĐÃ NÉN BỘ NHỚ) ===\n{summary}\n================================================="
            })
            
            non_sys_messages = [msg for msg in messages if msg["role"] != "system"]
            new_messages.extend(non_sys_messages[-3:])
            
            logger.info("Context compacted successfully. New history length: %d messages", len(new_messages))
            return new_messages
            
        return messages

    def _is_vietnamese(self, text: str) -> bool:
        vi_chars = set("áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ"
                       "ÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ")
        if any(c in vi_chars for c in text):
            return True
            
        vi_words = {
            "và", "của", "cho", "như", "được", "trong", "có", "một", "không", "tôi", 
            "bạn", "cậu", "tớ", "này", "đó", "nè", "nha", "đang", "là", "với", "hơn", 
            "lại", "nếu", "thế", "cái", "con", "gì", "nào", "ở", "về", "đã", "mới",
            "chào", "khoe", "học", "làm", "chơi"
        }
        words = [w.strip(",.!?()\"'").lower() for w in text.split()]
        if any(w in vi_words for w in words):
            return True
            
        return False

    async def chat(self, message: str | list, context: dict | None = None, image: str | None = None) -> str:
        """Đồng bộ chat: Gọi qua agent_loop và ghép các token văn bản lại."""
        text_parts = []
        async for chunk in self.chat_stream(message, context, image=image):
            if isinstance(chunk, str):
                text_parts.append(chunk)
            elif isinstance(chunk, dict) and chunk.get("type") == "text":
                text_parts.append(chunk["text"])
        return "".join(text_parts).strip()

    async def chat_stream(self, message: str | list, context: dict | None = None, image: str | None = None):
        """Streaming chat: Khởi tạo luồng agent_loop để trả về tokens và sự kiện duyệt."""
        context = context or {}

        companion_ctx = context.get("companion", {})
        time_note = companion_ctx.get("time_note", "")

        # Trích xuất plain text nếu message là danh sách multimodal
        plain_text = ""
        if isinstance(message, list):
            for part in message:
                if part.get("type") == "text":
                    plain_text += part["text"] + " "
            plain_text = plain_text.strip()
        else:
            plain_text = message

        # Lấy activity từ perception
        perception = context.get("perception", {})
        activity = perception.get("activity", "unknown")

        # ── Companion Intelligence: pull live state from engines ──────────
        _mood_state = None
        _emotion_label = "neutral"
        _goal_hint = ""
        try:
            from persona.mood.mood_engine import mood_engine
            from persona.emotion.emotion_engine import emotion_engine
            from persona.relationship.relationship_tracker import relationship_tracker
            from persona.goals.goal_manager import goal_manager
            from life.observe.observer import life_observer

            _mood_state    = mood_engine.state
            _emotion_label = emotion_engine.emotion
            rel_level      = relationship_tracker.level
            mood           = _mood_state.mood
            _goal_hint     = goal_manager.get_prompt_hint()

            # Record the user's message so the observer knows user is active
            life_observer.record_user_message()
        except Exception:
            rel_level = companion_ctx.get("rel_level", "Người quen")
            mood      = companion_ctx.get("mood", "vui vẻ")

        # ── EmpathyEngine: detect user emotion & update conversation ──────
        _empathy_prefix = ""
        try:
            from social.empathy.empathy_engine import empathy_engine
            from social.conversation.conversation_manager import conversation_manager
            from motivation.motivation_manager import motivation_manager
            from runtime.session.session_manager import session_manager

            reading = empathy_engine.analyze(plain_text)
            _empathy_prefix = empathy_engine.get_empathy_prefix(reading)

            conversation_manager.on_user_message(plain_text, reading.detected_emotion)
            motivation_manager.on_conversation(plain_text)
            session_manager.on_user_activity()
        except Exception:
            pass

        # ── MemoryManager: semantic recall for context ────────────────────
        try:
            from memory.memory_manager import memory_manager
            memory_manager.add_turn("user", plain_text)
            if plain_text and not context.get("memory"):
                recalled = memory_manager.recall_for_prompt(plain_text)
                if recalled:
                    context["memory"] = [{"text": s} for s in recalled]
        except Exception:
            pass



        force_eng = not self._is_vietnamese(plain_text)
        system_prompt = self._build_system_prompt(rel_level, mood, time_note, force_english=force_eng, activity=activity)

        # ── Inject dynamic companion state block ──────────────────────────
        try:
            from persona.dialogue.system_prompt import build_dynamic_state_block
            
            empathy_ctx = context.get("empathy") if context else None
            motivation_ctx = context.get("motivation") if context else None
            
            motivation_desc = motivation_ctx.get("description", "") if motivation_ctx else ""
            recommended_tone = empathy_ctx.get("recommended_tone", "neutral") if empathy_ctx else "neutral"
            
            state_block = build_dynamic_state_block(
                mood_state=_mood_state,
                emotion=_emotion_label,
                goal_hint=_goal_hint,
                motivation_desc=motivation_desc,
                recommended_tone=recommended_tone,
            )
            if state_block:
                system_prompt = system_prompt + "\n" + state_block
        except Exception:
            pass

        # ── Inject dynamic belief state block ──────────────────────────────
        try:
            if context and "beliefs" in context:
                belief_lines = []
                for b in context["beliefs"]:
                    if b.get("key", "").startswith("env.tool_broken.") and b.get("value") == "true":
                        tool_name = b["key"].split("env.tool_broken.")[-1]
                        belief_lines.append(f"- Công cụ '{tool_name}' hiện đang bị lỗi/hỏng trong hệ thống. ĐỪNG sử dụng nó.")
                    else:
                        belief_lines.append(f"- Niềm tin: {b.get('key')} = {b.get('value')}")
                if belief_lines:
                    system_prompt += "\n\n=== NIỀM TIN HIỆN TẠI (CURRENT BELIEFS) ===\n" + "\n".join(belief_lines)
        except Exception:
            pass

        messages = [{"role": "system", "content": system_prompt}]

        # Tầng 0.5: Tải danh sách kỹ năng khả dụng (lấy cảm hứng từ Hermes Agent)
        if self.skills_manager:
            try:
                skills = self.skills_manager.list_skills()
                if skills:
                    skills_lines = []
                    for s in skills:
                        skills_lines.append(f"- {s.get('name')}: {s.get('description')}")
                    
                    skills_block = (
                        "=== AVAILABLE SKILLS (KỸ NĂNG HỆ THỐNG KHẢ DỤNG) ===\n"
                        "Bạn có các kỹ năng đặc biệt sau đây được cài đặt. Để xem chi tiết hướng dẫn thực hiện "
                        "và áp dụng của một kỹ năng, hãy gọi công cụ `read_skill` với tên kỹ năng thích hợp:\n"
                        + "\n".join(skills_lines)
                    )
                    messages.append({
                        "role": "system",
                        "content": skills_block
                    })
            except Exception as e:
                logger.error(f"Failed to inject available skills to system prompt: {e}")

        # Tầng 1: PerceptionFusion - Nhúng thông tin nhận thức môi trường (Perception Packet)
        if perception:
            perception_lines = []
            ts = perception.get("timestamp")
            if ts:
                perception_lines.append(f"Thời gian hệ thống: {ts}")
            
            idle_sec = perception.get("idle_time_seconds", 0)
            if idle_sec >= 10:
                perception_lines.append(f"Người dùng đã không tương tác trong {int(idle_sec)} giây.")
                
            scr = perception.get("screen_text", "")
            if scr:
                perception_lines.append(f"Nội dung đang hiển thị trên màn hình người dùng (giới hạn 600 ký tự):\n{scr[:600]}")
                
            if perception_lines:
                messages.append({
                    "role": "system",
                    "content": "=== NHẬN THỨC MÔI TRƯỜNG HIỆN TẠI (PERCEPTION) ===\n" + "\n".join(perception_lines)
                })

        memory_facts = context.get("memory", [])
        if memory_facts:
            facts_text = "; ".join(f["text"] for f in memory_facts[-5:])
            messages.append({
                "role": "system",
                "content": f"Thông tin đã ghi nhớ về người dùng: {facts_text}"
            })

        rag_context = context.get("rag_context", "")
        if rag_context:
            messages.append({
                "role": "system",
                "content": f"Ngữ cảnh từ tài liệu người dùng (dùng để trả lời nếu liên quan):\n\n{rag_context}"
            })

        # Tự động chụp ảnh màn hình làm bối cảnh đầu vào nếu được kích hoạt desktopControl
        if not image and config.get("features.desktopControl", True):
            screenshot_b64 = _capture_screen_b64()
            if screenshot_b64:
                image = screenshot_b64

        # Đính kèm ảnh nếu có
        if image:
            image_url = image if image.startswith("data:") else f"data:image/png;base64,{image}"
            if isinstance(message, list):
                user_msg = {
                    "role": "user",
                    "content": message + [{"type": "image_url", "image_url": {"url": image_url}}]
                }
            else:
                user_msg = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": message},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
        else:
            user_msg = {"role": "user", "content": message}

        # Inject session history
        history = self._get_session_history()
        messages_with_history = messages + history[-20:] + [user_msg]

        # Bắt đầu vòng lặp Agent Loop
        full_reply_parts = []
        async for chunk in self._run_agent_loop(messages_with_history, force_eng):
            if isinstance(chunk, str):
                full_reply_parts.append(chunk)
            yield chunk

        full_reply = "".join(full_reply_parts).strip()
        if full_reply:
            self._append_to_history("user", plain_text)
            self._append_to_history("assistant", full_reply)

            # ── Post-response: update companion goals ──────
            try:
                from persona.goals.goal_manager import goal_manager
                # Try to auto-complete conversation-triggered goals
                goal_manager.try_complete_by_trigger("conversation")
            except Exception:
                pass

            # ── Post-response: MemoryManager + ConversationManager ────────
            try:
                from memory.memory_manager import memory_manager
                from social.conversation.conversation_manager import conversation_manager
                memory_manager.add_turn("assistant", full_reply)
                conversation_manager.on_assistant_message(full_reply)
            except Exception:
                pass

            # ── Post-response: MotivationManager task complete ────────────
            try:
                from motivation.motivation_manager import motivation_manager
                motivation_manager.on_conversation()
            except Exception:
                pass


    async def _run_agent_loop(self, messages: list[dict], force_eng: bool):
        provider, api_key, model, base_url = _get_llm_credentials()
        
        # Nạp động các MCP tools
        mcp_tools = []
        if self.mcp_manager:
            try:
                mcp_tools = await self.mcp_manager.get_all_tools()
            except Exception as e:
                logger.error(f"MCP: Lỗi khi lấy danh sách MCP tools: {e}")

        # Nạp động các Plugin tools
        plugin_tools = []
        if self.plugin_manager:
            try:
                plugin_tools = self.plugin_manager.get_tool_schemas()
            except Exception as e:
                logger.error(f"PluginManager: Lỗi khi lấy danh sách plugin tools: {e}")

        tools = []
        if config.get("features.desktopControl", True):
            tools.extend(TOOLS_SCHEMA)
        if mcp_tools:
            tools.extend(mcp_tools)
        if plugin_tools:
            tools.extend(plugin_tools)
            
        # Nếu đang chạy bằng Ollama, chêm thêm chỉ dẫn JSON Tool Calling vào Prompt Hệ thống
        if provider == "ollama":
            ollama_inst = OLLAMA_SYSTEM_INSTRUCTION
            if mcp_tools:
                ollama_inst += "\n\n=== MCP TOOLS (CÔNG CỤ MCP BỔ SUNG) ===\n"
                for i, tool in enumerate(mcp_tools, start=15):
                    t_name = tool["name"]
                    t_desc = tool.get("description", "Không có mô tả")
                    t_params = tool.get("parameters", {})
                    ollama_inst += f"{i}. `{t_name}`: {t_desc}. Tham số: {json.dumps(t_params, ensure_ascii=False)}\n"
            
            for msg in messages:
                if msg["role"] == "system":
                    msg["content"] += "\n" + ollama_inst
                    
        max_turns = config.get("agent.maxTurns", 30)
        turn = 0
        recent_failures = {}
        
        while turn < max_turns:
            # Tự động nén và tóm tắt hội thoại nếu gần đầy context limit
            messages = await self._compact_context_if_needed(messages, provider, api_key, model, base_url)
            turn += 1
            tool_calls_to_run = []
            response_text = ""
            stop_reason = None
            
            # 1. Gọi LLM API qua Provider adapter tương ứng
            provider_instance = None
            if provider == "gemini":
                if not api_key:
                    yield " Gemini API Key đang để trống."
                    return
                from llm.providers.gemini import GeminiProvider
                provider_instance = GeminiProvider()
            elif provider in ["openai", "deepseek", "glm", "qwen", "openai-compatible"]:
                if not api_key and provider != "openai-compatible":
                    yield f" {provider.upper()} API Key đang để trống."
                    return
                from llm.providers.openai import OpenAIProvider
                provider_instance = OpenAIProvider()
            else: # ollama
                from llm.providers.ollama import OllamaProvider
                provider_instance = OllamaProvider()

            try:
                res = provider_instance.chat_with_tools(
                    messages=messages,
                    api_key=api_key if api_key else "",
                    model=model,
                    base_url=base_url,
                    tools=tools
                )
                response_text = res.get("content", "") or ""
                tool_calls_to_run = res.get("tool_calls", []) or []
                stop_reason = res.get("finish_reason")
            except Exception as exc:
                logger.error("%s API tools error: %s", provider.upper(), exc)
                yield f" Có lỗi khi gọi {provider.upper()}: {exc}"
                return

            # Stream response_text to user if any
            if response_text:
                words = response_text.split(" ")
                for i, word in enumerate(words):
                    yield word + (" " if i < len(words) - 1 else "")
                    await asyncio.sleep(0.01)

            # Determine if we should stop the agent loop
            should_stop = False
            if not tool_calls_to_run:
                should_stop = True
            elif stop_reason in ["length", "MAX_TOKENS"]:
                should_stop = True

            if should_stop:
                break

            # 2. Xử lý các tool calls được kích hoạt
            if tool_calls_to_run:
                # Lưu intent gọi tool vào hội thoại
                if provider == "gemini":
                    parts = []
                    if response_text:
                        parts.append({"text": response_text})
                    for tc in tool_calls_to_run:
                        parts.append({"functionCall": {"name": tc["name"], "args": tc["args"]}})
                    messages.append({"role": "model", "parts": parts})
                elif provider in ["openai", "deepseek", "glm", "qwen", "openai-compatible"]:
                    openai_tcs = []
                    for tc in tool_calls_to_run:
                        openai_tcs.append({
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])}
                        })
                    messages.append({
                        "role": "assistant",
                        "content": response_text or None,
                        "tool_calls": openai_tcs
                    })
                else: # ollama
                    messages.append({"role": "assistant", "content": response_text})

                # Chạy các tools
                for tc in tool_calls_to_run:
                    t_name = tc["name"]
                    t_args = tc["args"]
                    t_id = tc["id"]
                    
                    from execution.approval.approval_registry import PermissionManager
                    need_approval = PermissionManager.requires_approval(t_name, t_args)
                    
                    approved = True
                    if need_approval:
                        req_id = f"req_{uuid.uuid4().hex[:8]}"
                        # Gửi sự kiện yêu cầu phê duyệt về Client
                        yield {
                            "type": "request_approval",
                            "req_id": req_id,
                            "action": t_name,
                            "details": t_args
                        }
                        # Đợi Client nhấn nút phê duyệt
                        approved = await wait_for_approval(req_id)
                        
                    if not approved:
                        t_output = {"success": False, "error": "Yêu cầu chạy hành động bị người dùng từ chối."}
                        yield f"\n[Hệ thống: Từ chối chạy {t_name}]\n"
                    else:
                        yield f"\n[Hệ thống: Đang thực thi {t_name}...]\n"
                        
                        # Theo dõi lặp lệnh lỗi (Self-correction check)
                        args_str = json.dumps(t_args, sort_keys=True)
                        fail_key = f"{t_name}:{args_str}"
                        fail_count = recent_failures.get(fail_key, 0)
                        
                        t_output = await execute_tool(t_name, t_args, mcp_manager=self.mcp_manager)
                        
                        # Self-correction log if command failed
                        if not t_output.get("success"):
                            recent_failures[fail_key] = fail_count + 1
                            if recent_failures[fail_key] >= 2:
                                t_output["system_warning"] = (
                                    f"CẢNH BÁO HỆ THỐNG: Công cụ '{t_name}' đã thất bại {recent_failures[fail_key]} lần liên tiếp với cùng tham số! "
                                    f"Vui lòng KHÔNG chạy lại y hệt. Hãy phân tích thông báo lỗi, kiểm tra cú pháp "
                                    f"hoặc sử dụng một phương pháp khác thay thế."
                                )
                            
                            err_msg = t_output.get('stderr') or t_output.get('error') or "Không rõ nguyên nhân"
                            yield f"\n[Hệ thống: Lệnh chạy thất bại với lỗi:\n{err_msg}]\n"
                        else:
                            yield f"\n[Hệ thống: Hoàn thành {t_name}]\n"
                            
                    # Cập nhật kết quả tool vào hội thoại
                    if provider == "gemini":
                        screenshot_b64 = _capture_screen_b64()
                        parts = [{"functionResponse": {"name": t_name, "response": {"output": t_output}}}]
                        if screenshot_b64:
                            parts.append({
                                "inlineData": {
                                    "mimeType": "image/png",
                                    "data": screenshot_b64
                                }
                            })
                        messages.append({
                            "role": "user",
                            "parts": parts
                        })
                    elif provider in ["openai", "deepseek", "glm", "qwen", "openai-compatible"]:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": t_id,
                            "name": t_name,
                            "content": json.dumps(t_output, ensure_ascii=False)
                        })
                        screenshot_b64 = _capture_screen_b64()
                        if screenshot_b64:
                            messages.append({
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Đây là ảnh chụp màn hình cập nhật sau khi thực thi công cụ:"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
                                ]
                            })
                    else: # ollama
                        messages.append({
                            "role": "user",
                            "content": f"Kết quả công cụ '{t_name}': {json.dumps(t_output, ensure_ascii=False)}"
                        })

# Global singleton
llm_service = LLMService()