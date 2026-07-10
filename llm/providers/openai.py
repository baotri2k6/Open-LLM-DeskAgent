"""OpenAI Compatible provider adapter."""

from __future__ import annotations

import json
import urllib.request
from typing import Any
from llm.providers.base import BaseLLMProvider


def _to_openai_tools(tools_list: list) -> list:
    openai_tools = []
    for tool in tools_list:
        openai_tools.append({
            "type": "function",
            "function": tool
        })
    return openai_tools


class OpenAIProvider(BaseLLMProvider):
    """OpenAI, DeepSeek, GLM, Qwen, and custom OpenAI Compatible provider adapter."""

    def chat_with_tools(
        self,
        messages: list[dict],
        api_key: str,
        model: str,
        base_url: str,
        tools: list[dict] | None = None
    ) -> dict:
        url = base_url.rstrip("/")
        if not url.endswith("/chat/completions") and not url.endswith("/completions"):
            url = f"{url}/chat/completions"
            
        openai_tools = _to_openai_tools(tools) if tools else None
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        if openai_tools:
            payload["tools"] = openai_tools
            
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
            res = json.loads(resp.read().decode("utf-8"))
            
        choice = res["choices"][0]
        msg = choice["message"]
        response_text = msg.get("content") or ""
        finish_reason = choice.get("finish_reason")
        
        tool_calls_to_run = []
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            for tc in tool_calls:
                tool_calls_to_run.append({
                    "id": tc.get("id"),
                    "name": tc["function"].get("name"),
                    "args": json.loads(tc["function"].get("arguments", "{}"))
                })
                
        return {
            "content": response_text,
            "tool_calls": tool_calls_to_run,
            "finish_reason": finish_reason
        }
