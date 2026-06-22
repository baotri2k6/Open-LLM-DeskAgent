"""LLM facade — Ollama backend with graceful fallback."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
import asyncio
import queue
import threading
from core.config import config
from core.logger import get_logger
from persona.system_prompt import build_system_prompt
from persona.persona_manager import PersonaManager

logger = get_logger("ai-companion.llm")

OLLAMA_URL = "http://127.0.0.1:11434"


def _get_model() -> str:
    return config.get("llm.model", "qwen2.5:1.5b")


def _get_provider() -> str:
    return config.get("llm.provider", "ollama")


def _ollama_chat(messages: list[dict], model: str) -> str:
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["message"]["content"].strip()


def _ollama_chat_stream(messages: list[dict], model: str):
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        while True:
            line = resp.readline()
            if not line:
                break
            data = json.loads(line.decode("utf-8"))
            content = data.get("message", {}).get("content", "")
            if content:
                yield content


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
            contents.append({
                "role": mapped_role,
                "parts": [{"text": content}]
            })
            
    return contents, system_instruction


def _gemini_chat(contents: list, system_instruction: dict | None, api_key: str, model: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = system_instruction
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _gemini_stream(contents: list, system_instruction: dict | None, api_key: str, model: str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
    payload = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = system_instruction
        
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if not line_str.startswith("data:"):
                continue
            data_content = line_str.removeprefix("data:").strip()
            try:
                chunk = json.loads(data_content)
                text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                if text:
                    yield text
            except Exception:
                pass


def _openai_chat(messages: list, api_key: str, model: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()


def _openai_stream(messages: list, api_key: str, model: str):
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if not line_str.startswith("data:"):
                continue
            data_content = line_str.removeprefix("data:").strip()
            if data_content == "[DONE]":
                break
            try:
                chunk = json.loads(data_content)
                text = chunk["choices"][0]["delta"].get("content", "")
                if text:
                    yield text
            except Exception:
                pass


class ThreadedGenerator:
    def __init__(self, sync_generator, *args, **kwargs):
        self.sync_generator = sync_generator
        self.args = args
        self.kwargs = kwargs
        self.q = queue.Queue(maxsize=200)
        self.done = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        try:
            for item in self.sync_generator(*self.args, **self.kwargs):
                self.q.put(item)
        except Exception as e:
            self.q.put(e)
        finally:
            self.done = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        while True:
            try:
                item = self.q.get_nowait()
                if isinstance(item, Exception):
                    raise item
                return item
            except queue.Empty:
                if self.done and self.q.empty():
                    raise StopAsyncIteration
                await asyncio.sleep(0.005)


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

        provider = _get_provider()
        provider_err_msg = None
        
        if provider == "gemini":
            api_key = config.get("llm.gemini_api_key", "")
            if api_key:
                try:
                    gemini_model = config.get("llm.gemini_model", "gemini-1.5-flash")
                    contents, system_instruction = _to_gemini_format(messages)
                    reply = _gemini_chat(contents, system_instruction, api_key, gemini_model)
                    logger.info("Gemini API replied (%d chars)", len(reply))
                    return reply
                except Exception as exc:
                    provider_err_msg = f"API call failed: {exc}"
                    logger.warning("Gemini API failed, falling back to Ollama: %s", exc)
            else:
                provider_err_msg = "API Key is empty"
                logger.warning("Gemini API Key is empty, falling back to Ollama")
                
        elif provider == "openai":
            api_key = config.get("llm.openai_api_key", "")
            if api_key:
                try:
                    openai_model = config.get("llm.openai_model", "gpt-4o-mini")
                    reply = _openai_chat(messages, api_key, openai_model)
                    logger.info("OpenAI API replied (%d chars)", len(reply))
                    return reply
                except Exception as exc:
                    provider_err_msg = f"API call failed: {exc}"
                    logger.warning("OpenAI API failed, falling back to Ollama: %s", exc)
            else:
                provider_err_msg = "API Key is empty"
                logger.warning("OpenAI API Key is empty, falling back to Ollama")

        # Fallback to Ollama
        model = _get_model()
        try:
            reply = _ollama_chat(messages, model)
            logger.info("Ollama replied (%d chars)", len(reply))
            return reply
        except urllib.error.URLError as exc:
            logger.warning("Ollama not reachable: %s", exc)
            if provider_err_msg:
                return (
                    f"Không thể kết nối đến {provider.upper()} ({provider_err_msg}). "
                    "Hệ thống đã thử chuyển sang Ollama local nhưng cũng không kết nối được. "
                    "Bạn hãy chạy 'ollama serve' hoặc kiểm tra cấu hình API Key/mạng nhé."
                )
            return (
                "Minh chưa kết nối được với Ollama. "
                "Bạn hãy chạy 'ollama serve' rồi thử lại nhé."
            )
        except Exception as exc:
            logger.error("LLM error: %s", exc)
            return f"Có lỗi khi xử lý: {exc}"

    async def chat_stream(self, message: str, context: dict | None = None):
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

        provider = _get_provider()
        provider_err_msg = None
        
        if provider == "gemini":
            api_key = config.get("llm.gemini_api_key", "")
            if api_key:
                try:
                    gemini_model = config.get("llm.gemini_model", "gemini-1.5-flash")
                    contents, system_instruction = _to_gemini_format(messages)
                    async for token in ThreadedGenerator(_gemini_stream, contents, system_instruction, api_key, gemini_model):
                        yield token
                    return
                except Exception as exc:
                    provider_err_msg = f"API call failed: {exc}"
                    logger.warning("Gemini API failed, falling back to Ollama: %s", exc)
            else:
                provider_err_msg = "API Key is empty"
                logger.warning("Gemini API Key is empty, falling back to Ollama")
                
        elif provider == "openai":
            api_key = config.get("llm.openai_api_key", "")
            if api_key:
                try:
                    openai_model = config.get("llm.openai_model", "gpt-4o-mini")
                    async for token in ThreadedGenerator(_openai_stream, messages, api_key, openai_model):
                        yield token
                    return
                except Exception as exc:
                    provider_err_msg = f"API call failed: {exc}"
                    logger.warning("OpenAI API failed, falling back to Ollama: %s", exc)
            else:
                provider_err_msg = "API Key is empty"
                logger.warning("OpenAI API Key is empty, falling back to Ollama")

        # Fallback to Ollama
        model = _get_model()
        try:
            async for token in ThreadedGenerator(_ollama_chat_stream, messages, model):
                yield token
        except urllib.error.URLError as exc:
            logger.warning("Ollama not reachable: %s", exc)
            if provider_err_msg:
                yield (
                    f"Không thể kết nối đến {provider.upper()} ({provider_err_msg}). "
                    "Hệ thống đã thử chuyển sang Ollama local nhưng cũng không kết nối được. "
                    "Bạn hãy chạy 'ollama serve' hoặc kiểm tra cấu hình API Key/mạng nhé."
                )
            else:
                yield "Mình chưa kết nối được với Ollama. Bạn hãy chạy 'ollama serve' rồi thử lại nhé."
        except Exception as exc:
            logger.error("LLM error: %s", exc)
            yield f" Có lỗi khi xử lý: {exc}"