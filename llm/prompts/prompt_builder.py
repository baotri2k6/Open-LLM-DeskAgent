"""Builds structured prompts for LLM calls with history truncation, role mapping, and multimodal support."""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ai-companion.llm.prompts")


class PromptBuilder:
    """Orchestrates building the system prompt and conversation messages list for LLMs.
    
    Includes history truncation, role mapping, and multimodal image injection.
    """

    def __init__(self) -> None:
        pass

    def build_messages(
        self,
        system_instruction: str,
        history: List[Dict[str, Any]],
        new_prompt: str,
        image_base64: Optional[str] = None,
        max_history_turns: int = 20,
    ) -> List[Dict[str, Any]]:
        """Combine system instruction, chat history, and new prompt into final LLM messages format.
        
        Args:
            system_instruction: Core system prompt rules.
            history: List of past conversation turns: [{"role": "user"|"assistant", "content": "..."}]
            new_prompt: The latest user message.
            image_base64: Optional base64 encoded image to append to the user query (for multimodal inputs).
            max_history_turns: Maximum number of previous conversation turns to retain to avoid context overflow.
            
        Returns:
            A list of message dicts formatted for the LLM API.
        """
        messages: List[Dict[str, Any]] = []

        # 1. Inject System instruction
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        # 2. Process and filter history
        # Truncate history to only keep the last N turns
        truncated_history = history[-max_history_turns:] if len(history) > max_history_turns else history

        for turn in truncated_history:
            role = turn.get("role")
            content = turn.get("content") or turn.get("text", "")
            
            # Map roles if needed (e.g. standardizing user/assistant)
            if role in ["user", "human"]:
                llm_role = "user"
            elif role in ["assistant", "bot", "model"]:
                llm_role = "assistant"
            elif role == "system":
                # Avoid duplicating system instructions
                continue
            else:
                llm_role = "user"

            # Avoid adding empty messages
            if content:
                messages.append({"role": llm_role, "content": content})

        # 3. Process new user query
        user_message: Dict[str, Any] = {"role": "user"}

        if image_base64:
            # Multi-modal input format: list of content parts
            user_message["content"] = [
                {"type": "text", "text": new_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                }
            ]
        else:
            user_message["content"] = new_prompt

        messages.append(user_message)
        return messages


# Global singleton
prompt_builder = PromptBuilder()
