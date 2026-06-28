"""Ollama provider adapter."""

from __future__ import annotations

import json
import urllib.request
import uuid
from typing import Any
from llm.providers.base import BaseLLMProvider
from llm.providers.openai import _to_openai_tools


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


def _parse_json_fallback(text: str) -> dict | None:
    """Parse JSON block from response text if assistant output is raw JSON string."""
    import re
    text_clean = text.strip()
    match = re.search(r"\{.*\}", text_clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None


class OllamaProvider(BaseLLMProvider):
    """Ollama provider adapter for local hosting."""

    def chat_with_tools(
        self,
        messages: list[dict],
        api_key: str,
        model: str,
        base_url: str,
        tools: list[dict] | None = None
    ) -> dict:
        formatted_messages = _to_ollama_format(messages)
        ollama_tools = _to_openai_tools(tools) if tools else None
        
        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": False,
        }
        if ollama_tools:
            payload["tools"] = ollama_tools
            
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            
        msg = res.get("message", {})
        response_text = msg.get("content") or ""
        finish_reason = res.get("done_reason")
        
        tool_calls_to_run = []
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            for tc in tool_calls:
                tool_calls_to_run.append({
                    "id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                    "name": tc["function"].get("name"),
                    "args": tc["function"].get("arguments", {})
                })
                
        # Fallback JSON parser
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
                    response_text = ""  # Hide JSON code from chat
                    
        return {
            "content": response_text,
            "tool_calls": tool_calls_to_run,
            "finish_reason": finish_reason
        }
