"""Base LLM provider interface."""

from __future__ import annotations

from typing import Any

class BaseLLMProvider:
    def chat_with_tools(
        self,
        messages: list[dict],
        api_key: str,
        model: str,
        base_url: str,
        tools: list[dict] | None = None
    ) -> dict:
        """Call the LLM API with optional tool schemas.
        
        Returns a dict with format:
        {
            "content": str,
            "tool_calls": list[dict], # [{"id": str, "name": str, "args": dict}]
            "finish_reason": str
        }
        """
        raise NotImplementedError
