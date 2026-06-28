"""ResponseParser — phân tích cú pháp và trích xuất thông tin từ phản hồi của LLM.

Trích xuất khối suy nghĩ (<think>...</think>), thẻ cảm xúc ([emotion]), và định dạng tool calls fallback.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai-companion.cognition.parser")


@dataclass
class ParsedResponse:
    """Kết quả phân tích phản hồi LLM."""
    clean_text:  str = ""
    thought:     str = ""
    emotion:     str = "neutral"
    tool_calls:  List[Dict[str, Any]] = field(default_factory=list)


class ResponseParser:
    """Phân tích cú pháp văn bản sinh ra từ LLM."""

    def __init__(self) -> None:
        pass

    def parse(self, text: str) -> ParsedResponse:
        """Phân tích toàn bộ văn bản phản hồi.

        Args:
            text: Văn bản thô từ LLM.
        """
        result = ParsedResponse()
        
        # 1. Trích xuất block suy nghĩ <think>...</think>
        thought_match = re.search(r"<think>([\s\S]*?)</think>", text)
        if thought_match:
            result.thought = thought_match.group(1).strip()
            # Loại bỏ thẻ think khỏi clean text
            text = text.replace(thought_match.group(0), "")
            
        # 2. Trích xuất emotion tag dạng [vui vẻ] hoặc [emotion:happy]
        emotion_match = re.search(r"\[(?:emotion:)?([a-zA-Z\s\u00C0-\u1EF9]+)\]", text)
        if emotion_match:
            result.emotion = emotion_match.group(1).strip()
            # Loại bỏ thẻ emotion khỏi clean text
            text = text.replace(emotion_match.group(0), "")

        # 3. Trích xuất fallback JSON tool call dạng ```json ... ```
        json_blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        for block in json_blocks:
            try:
                data = json.loads(block.strip())
                # Nhận diện cấu hình tool call
                tool_name = data.get("tool") or data.get("action")
                tool_args = data.get("args") or data.get("arguments") or {}
                if tool_name:
                    result.tool_calls.append({
                        "name": tool_name,
                        "args": tool_args
                    })
                    # Xoá khối code để clean_text sạch
                    text = text.replace(f"```json\n{block}\n```", "").replace(f"```\n{block}\n```", "")
            except Exception:
                pass

        result.clean_text = text.strip()
        return result


# Global singleton
response_parser = ResponseParser()
