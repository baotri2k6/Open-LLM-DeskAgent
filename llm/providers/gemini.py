"""Google Gemini provider adapter."""

from __future__ import annotations

import json
import urllib.request
from typing import Any
from llm.providers.base import BaseLLMProvider


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


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider adapter."""

    def chat_with_tools(
        self,
        messages: list[dict],
        api_key: str,
        model: str,
        base_url: str,
        tools: list[dict] | None = None
    ) -> dict:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        contents, system_instruction = _to_gemini_format(messages)
        gemini_tools = _to_gemini_tools(tools) if tools else None
        
        payload = {"contents": contents}
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        if gemini_tools:
            payload["tools"] = gemini_tools
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            
        candidate = res["candidates"][0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        finish_reason = candidate.get("finishReason")
        
        response_text = ""
        tool_calls_to_run = []
        for part in parts:
            if "text" in part:
                response_text += part["text"]
            if "functionCall" in part:
                func = part["functionCall"]
                tool_calls_to_run.append({
                    "id": func.get("name"),
                    "name": func.get("name"),
                    "args": func.get("args", {})
                })
                
        return {
            "content": response_text,
            "tool_calls": tool_calls_to_run,
            "finish_reason": finish_reason
        }
