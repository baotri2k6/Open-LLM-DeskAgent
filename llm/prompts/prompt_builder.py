"""Builds structured prompts for LLM calls."""

from __future__ import annotations

from typing import List, Dict
from persona.dialogue.system_prompt import build_system_prompt


class PromptBuilder:
    """Orchestrates building the system prompt and conversation messages list for LLMs."""

    def __init__(self) -> None:
        pass

    def build_messages(
        self,
        system_instruction: str,
        history: List[Dict[str, str]],
        new_prompt: str
    ) -> List[Dict[str, str]]:
        """Combine system instruction, chat history, and new prompt into final LLM messages format."""
        messages = [{"role": "system", "content": system_instruction}]
        
        # Extend with chat history turns
        messages.extend(history)
        
        # Append new user prompt
        messages.append({"role": "user", "content": new_prompt})
        return messages


# Global singleton
prompt_builder = PromptBuilder()
