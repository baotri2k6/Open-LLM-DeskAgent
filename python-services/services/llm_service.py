"""LLM facade — Ollama/Gemini/OpenAI backend supporting OS Agent and local tool calling fallback."""

from __future__ import annotations

import json
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
from agents.desktop_agent import DesktopAgent
from utils.approval_registry import wait_for_approval

logger = get_logger("ai-companion.llm")

OLLAMA_URL = "http://127.0.0.1:11434"


def _get_model() -> str:
    return config.get("llm.model", "qwen2.5:1.5b")


def _get_provider() -> str:
    return config.get("llm.provider", "ollama")


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


def _openai_chat_with_tools(messages: list, api_key: str, model: str, tools: list | None = None) -> dict:
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    if tools:
        payload["tools"] = tools
        
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _ollama_chat_with_tools(messages: list[dict], model: str, tools: list | None = None) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def execute_tool(name: str, args: dict) -> dict:
    """Gọi thực thi tool tương ứng dựa trên tên và các đối số."""
    try:
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
            agent = DesktopAgent()
            return await agent.open_application(args.get("app_name", ""))
        elif name == "search_google":
            return search_google(args.get("query", ""))
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
    }
]


class LLMService:
    def __init__(self) -> None:
        self.persona_mgr = PersonaManager()
        self._persona = self.persona_mgr.load_persona("icegirl")
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self, rel_level: str = "Người quen", mood: str = "vui vẻ", time_note: str = "", force_english: bool = False) -> str:
        avatar_model = config.get("app.avatarModel", "IceGirl")
        persona_name = "icegirl"
        if "hiyori" in avatar_model.lower():
            persona_name = "hiyori"
        elif "mao" in avatar_model.lower():
            persona_name = "mao"
        elif "huohuo" in avatar_model.lower():
            persona_name = "huohuo"
        
        self._persona = self.persona_mgr.load_persona(persona_name)
        return build_system_prompt(self._persona, rel_level, mood, time_note, force_english=force_english)

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

    async def chat(self, message: str, context: dict | None = None) -> str:
        """Đồng bộ chat: Gọi qua agent_loop và ghép các token văn bản lại."""
        text_parts = []
        async for chunk in self.chat_stream(message, context):
            if isinstance(chunk, str):
                text_parts.append(chunk)
            elif isinstance(chunk, dict) and chunk.get("type") == "text":
                text_parts.append(chunk["text"])
        return "".join(text_parts).strip()

    async def chat_stream(self, message: str, context: dict | None = None):
        """Streaming chat: Khởi tạo luồng agent_loop để trả về tokens và sự kiện duyệt."""
        context = context or {}

        companion_ctx = context.get("companion", {})
        rel_level = companion_ctx.get("rel_level", "Người quen")
        mood = companion_ctx.get("mood", "vui vẻ")
        time_note = companion_ctx.get("time_note", "")
        force_eng = not self._is_vietnamese(message)
        system_prompt = self._build_system_prompt(rel_level, mood, time_note, force_english=force_eng)

        messages = [{"role": "system", "content": system_prompt}]

        # Tầng 1: PerceptionFusion - Nhúng thông tin nhận thức môi trường (Perception Packet)
        perception = context.get("perception", {})
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

        messages.append({"role": "user", "content": message})

        # Bắt đầu vòng lặp Agent Loop
        async for chunk in self._run_agent_loop(messages, force_eng):
            yield chunk

    async def _run_agent_loop(self, messages: list[dict], force_eng: bool):
        provider = _get_provider()
        model = _get_model()
        tools = TOOLS_SCHEMA
        
        # Nếu đang chạy bằng Ollama, chêm thêm chỉ dẫn JSON Tool Calling vào Prompt Hệ thống
        if provider == "ollama":
            for msg in messages:
                if msg["role"] == "system":
                    msg["content"] += "\n" + OLLAMA_SYSTEM_INSTRUCTION
                    
        max_turns = 10
        turn = 0
        
        while turn < max_turns:
            turn += 1
            tool_calls_to_run = []
            response_text = ""
            
            # 1. Gọi LLM API
            if provider == "gemini":
                api_key = config.get("llm.gemini_api_key", "")
                gemini_model = config.get("llm.gemini_model", "gemini-1.5-flash")
                if api_key:
                    try:
                        contents, sys_instr_dict = _to_gemini_format(messages)
                        gemini_tools = _to_gemini_tools(tools) if config.get("features.desktopControl", True) else None
                        res = _gemini_chat_with_tools(contents, sys_instr_dict, api_key, gemini_model, gemini_tools)
                        
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
                    
            elif provider == "openai":
                api_key = config.get("llm.openai_api_key", "")
                openai_model = config.get("llm.openai_model", "gpt-4o-mini")
                if api_key:
                    try:
                        openai_tools = _to_openai_tools(tools) if config.get("features.desktopControl", True) else None
                        res = _openai_chat_with_tools(messages, api_key, openai_model, openai_tools)
                        
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
                        logger.error("OpenAI API tools error: %s", exc)
                        yield f" Có lỗi khi gọi OpenAI: {exc}"
                        return
                else:
                    yield " OpenAI API Key đang để trống."
                    return
                    
            else: # ollama
                try:
                    ollama_tools = _to_openai_tools(tools) if config.get("features.desktopControl", True) else None
                    res = _ollama_chat_with_tools(messages, model, ollama_tools)
                    
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
                elif provider == "openai":
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
                        t_output = await execute_tool(t_name, t_args)
                        
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
                    elif provider == "openai":
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