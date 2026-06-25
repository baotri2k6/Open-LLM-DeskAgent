"""LLM facade — Ollama/Gemini/OpenAI backend supporting OS Agent and local tool calling fallback."""

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
from core.config import config
from core.logger import get_logger
from persona.system_prompt import build_system_prompt
from persona.persona_manager import PersonaManager

# Import tools
from tools.computer_control import mouse_click, mouse_move, keyboard_type, keyboard_press, execute_command
from tools.file_writer import write_to_file
from tools.file_reader import read_file
from tools.browser_control import search_google, open_url
from tools.mxh_tools import search_twitter, read_reddit_post, get_youtube_transcript, search_bilibili, read_webpage_jina
from utils.approval_registry import wait_for_approval
from core.plugin_manager import PluginManager

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


def _to_gemini_format(messages: list[dict]) -> tuple[list[dict], dict | None]:
    contents = []
    system_instruction = None
    
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        
        if role == "system":
            if system_instruction is None:
                system_instruction = {"parts": [{"text": content}]}
            else:
                system_instruction["parts"][0]["text"] += "\n" + content
        else:
            mapped_role = "user" if role == "user" else "model"
            parts = []
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        parts.append({"text": item["text"]})
                    elif item.get("type") == "image_url":
                        img_url = item["image_url"]["url"]
                        if img_url.startswith("data:"):
                            header, b64_data = img_url.split(",", 1)
                            mime_type = header.split(";")[0].split(":")[1]
                            parts.append({
                                "inlineData": {
                                    "mimeType": mime_type,
                                    "data": b64_data
                                }
                            })
            else:
                if content:
                    parts.append({"text": content})
            if "functionCall" in msg:
                parts.append({"functionCall": msg["functionCall"]})
            if "functionResponse" in msg:
                parts.append({"functionResponse": msg["functionResponse"]})
                
            contents.append({
                "role": mapped_role,
                "parts": parts
            })
            
    return contents, system_instruction


def _to_gemini_tools(tools_list: list) -> list:
    def convert_schema(schema: dict) -> dict:
        new_schema = {}
        for k, v in schema.items():
            if k == "type":
                new_schema[k] = str(v).upper()
            elif isinstance(v, dict):
                new_schema[k] = convert_schema(v)
            else:
                new_schema[k] = v
        return new_schema
        
    gemini_funcs = []
    for tool in tools_list:
        gemini_funcs.append({
            "name": tool["name"],
            "description": tool["description"],
            "parameters": convert_schema(tool["parameters"])
        })
    return [{"functionDeclarations": gemini_funcs}]


def _to_openai_tools(tools_list: list) -> list:
    openai_tools = []
    for tool in tools_list:
        openai_tools.append({
            "type": "function",
            "function": tool
        })
    return openai_tools


def _gemini_chat_with_tools(contents: list, system_instruction: dict | None, api_key: str, model: str, tools: list | None = None) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = system_instruction
    if tools:
        payload["tools"] = tools
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _openai_chat_with_tools(messages: list, api_key: str, model: str, base_url: str, tools: list | None = None) -> dict:
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions") and not url.endswith("/completions"):
        url = f"{url}/chat/completions"
        
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    if tools:
        payload["tools"] = tools
        
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _to_ollama_format(messages: list[dict]) -> list[dict]:
    ollama_messages = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        new_msg = {"role": role}
        
        if isinstance(content, list):
            text_parts = []
            images = []
            for item in content:
                if item.get("type") == "text":
                    text_parts.append(item["text"])
                elif item.get("type") == "image_url":
                    img_url = item["image_url"]["url"]
                    if img_url.startswith("data:"):
                        try:
                            _, b64_data = img_url.split(",", 1)
                            images.append(b64_data)
                        except Exception:
                            pass
            new_msg["content"] = "\n".join(text_parts)
            if images:
                new_msg["images"] = images
        else:
            new_msg["content"] = content
            
        for k in ["tool_calls", "functionCall", "functionResponse"]:
            if k in msg:
                new_msg[k] = msg[k]
        ollama_messages.append(new_msg)
    return ollama_messages


def _ollama_chat_with_tools(messages: list[dict], model: str, base_url: str, tools: list | None = None) -> dict:
    formatted_messages = _to_ollama_format(messages)
    payload = {
        "model": model,
        "messages": formatted_messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
        elif name == "keyboard_type":
            return keyboard_type(args.get("text", ""))
        elif name == "keyboard_press":
            return keyboard_press(args.get("keys", ""))
        elif name == "open_application":
            from agents.desktop_agent import DesktopAgent
            agent = DesktopAgent()
            return await agent.open_application(args.get("app_name", ""))
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
6. `keyboard_type` (args: `text`): Gõ phím.
7. `keyboard_press` (args: `keys`): Nhấn phím nóng.
8. `open_application` (args: `app_name`): Mở ứng dụng.
9. `search_google` (args: `query`): Tìm kiếm Google.
10. `search_twitter` (args: `query`, `limit`): Tìm kiếm bài đăng trên Twitter/X.
11. `read_reddit_post` (args: `subreddit`, `limit`): Đọc bài viết hot trên Reddit.
12. `get_youtube_transcript` (args: `video_url`): Tải phụ đề video YouTube.
13. `search_bilibili` (args: `query`, `limit`): Tìm video trên Bilibili.
14. `read_webpage_jina` (args: `url`): Đọc toàn bộ nội dung của trang web.

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
    }
]


class LLMService:
    _conversation_history: list[dict[str, str]] = []
    _mcp_manager = None
    _plugin_manager = None

    def __init__(self) -> None:
        self.persona_mgr = PersonaManager()
        self._persona = self.persona_mgr.load_persona("icegirl")
        self._system_prompt = self._build_system_prompt()
        
        # Tích hợp MCP dạng Singleton
        if LLMService._mcp_manager is None:
            try:
                from core.mcp.server_registry import ServerRegistry
                from core.mcp.mcp_client import MCPClientManager
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

    @property
    def mcp_manager(self):
        return LLMService._mcp_manager

    @property
    def plugin_manager(self):
        return LLMService._plugin_manager

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
        rel_level = companion_ctx.get("rel_level", "Người quen")
        mood = companion_ctx.get("mood", "vui vẻ")
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

        force_eng = not self._is_vietnamese(plain_text)
        system_prompt = self._build_system_prompt(rel_level, mood, time_note, force_english=force_eng, activity=activity)

        messages = [{"role": "system", "content": system_prompt}]

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
                    
        max_turns = 10
        turn = 0
        
        while turn < max_turns:
            turn += 1
            tool_calls_to_run = []
            response_text = ""
            
            # 1. Gọi LLM API
            if provider == "gemini":
                if api_key:
                    try:
                        contents, sys_instr_dict = _to_gemini_format(messages)
                        gemini_tools = _to_gemini_tools(tools) if tools else None
                        res = _gemini_chat_with_tools(contents, sys_instr_dict, api_key, model, gemini_tools)
                        
                        candidate = res["candidates"][0]
                        content = candidate.get("content", {})
                        parts = content.get("parts", [])
                        
                        assistant_content = ""
                        for part in parts:
                            if "text" in part:
                                assistant_content += part["text"]
                            if "functionCall" in part:
                                func = part["functionCall"]
                                tool_calls_to_run.append({
                                    "id": func.get("name"),
                                    "name": func.get("name"),
                                    "args": func.get("args", {})
                                })
                        response_text = assistant_content
                    except Exception as exc:
                        logger.error("Gemini API tools error: %s", exc)
                        yield f" Có lỗi khi gọi Gemini: {exc}"
                        return
                else:
                    yield " Gemini API Key đang để trống."
                    return
                    
            elif provider in ["openai", "deepseek", "glm", "qwen", "openai-compatible"]:
                if api_key or provider == "openai-compatible":
                    try:
                        openai_tools = _to_openai_tools(tools) if tools else None
                        res = _openai_chat_with_tools(messages, api_key, model, base_url, openai_tools)
                        
                        msg = res["choices"][0]["message"]
                        response_text = msg.get("content") or ""
                        tool_calls = msg.get("tool_calls")
                        if tool_calls:
                            for tc in tool_calls:
                                tool_calls_to_run.append({
                                    "id": tc.get("id"),
                                    "name": tc["function"].get("name"),
                                    "args": json.loads(tc["function"].get("arguments", "{}"))
                                })
                    except Exception as exc:
                        logger.error("%s API tools error: %s", provider.upper(), exc)
                        yield f" Có lỗi khi gọi {provider.upper()}: {exc}"
                        return
                else:
                    yield f" {provider.upper()} API Key đang để trống."
                    return
                    
            else: # ollama
                try:
                    ollama_tools = _to_openai_tools(tools) if tools else None
                    res = _ollama_chat_with_tools(messages, model, base_url, ollama_tools)
                    
                    msg = res.get("message", {})
                    response_text = msg.get("content") or ""
                    
                    # Thử lọc native tool calls
                    tool_calls = msg.get("tool_calls")
                    if tool_calls:
                        for tc in tool_calls:
                            tool_calls_to_run.append({
                                    "id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                                    "name": tc["function"].get("name"),
                                    "args": tc["function"].get("arguments", {})
                            })
                            
                    # Fallback JSON parser nếu không tìm thấy native tool calls
                    if not tool_calls_to_run and response_text:
                        parsed = _parse_json_fallback(response_text)
                        if parsed:
                            tool_name = parsed.get("tool") or parsed.get("action")
                            tool_args = parsed.get("args") or parsed.get("arguments") or {}
                            if tool_name:
                                tool_calls_to_run.append({
                                    "id": f"call_{uuid.uuid4().hex[:8]}",
                                    "name": tool_name,
                                    "args": tool_args
                                })
                except Exception as exc:
                    logger.error("Ollama tools error: %s", exc)
                    yield f" Có lỗi khi kết nối tới Ollama local: {exc}"
                    return
 
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
                    
                    is_dangerous = t_name in ["execute_command", "write_to_file"]
                    auto_mode = config.get("agent.autoMode", False)
                    
                    approved = True
                    if is_dangerous and not auto_mode:
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
                        t_output = await execute_tool(t_name, t_args, mcp_manager=self.mcp_manager)
                        
                        # Self-correction log if command failed
                        if t_name == "execute_command" and not t_output.get("success"):
                            yield f"\n[Hệ thống: Lệnh chạy thất bại với lỗi:\n{t_output.get('stderr') or t_output.get('error')}]\n"
                        else:
                            yield f"\n[Hệ thống: Hoàn thành {t_name}]\n"
                            
                    # Cập nhật kết quả tool vào hội thoại
                    if provider == "gemini":
                        messages.append({
                            "role": "user",
                            "parts": [{"functionResponse": {"name": t_name, "response": {"output": t_output}}}]
                        })
                    elif provider in ["openai", "deepseek", "glm", "qwen", "openai-compatible"]:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": t_id,
                            "name": t_name,
                            "content": json.dumps(t_output, ensure_ascii=False)
                        })
                    else: # ollama
                        messages.append({
                            "role": "user",
                            "content": f"Kết quả công cụ '{t_name}': {json.dumps(t_output, ensure_ascii=False)}"
                        })
                continue
            else:
                # Không còn yêu cầu gọi tool nữa -> Đây là câu trả lời cuối cùng
                words = response_text.split(" ")
                for i, word in enumerate(words):
                    yield word + (" " if i < len(words) - 1 else "")
                    await asyncio.sleep(0.01)
                break