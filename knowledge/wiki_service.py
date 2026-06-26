"""Wiki Service — Auto-consolidates user profile, facts, and preferences from conversation history."""

from __future__ import annotations

import os
from pathlib import Path
from config.config import PROJECT_ROOT
from runtime.logger import get_logger
from llm.manager import LLMService

logger = get_logger("ai-companion.wiki")

class WikiService:
    _instance: WikiService | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(WikiService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.wiki_path = PROJECT_ROOT / "data" / "wiki_knowledge.md"
        # Ensure data folder exists
        self.wiki_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = True

    def get_knowledge(self) -> str:
        """Reads the consolidated wiki knowledge file."""
        if not self.wiki_path.exists():
            return ""
        try:
            with open(self.wiki_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read wiki knowledge: {e}")
            return ""

    async def consolidate_knowledge_async(self, conversation_history: list[dict[str, str]]) -> None:
        """Analyze conversation history asynchronously to update the wiki knowledge."""
        if not conversation_history or len(conversation_history) < 2:
            return

        # Prepare chat log text for LLM
        chat_log = []
        for msg in conversation_history[-10:]: # Look at last 10 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            chat_log.append(f"{role}: {content}")
        chat_log_str = "\n".join(chat_log)

        existing_knowledge = self.get_knowledge()
        
        prompt = (
            f"You are a background cognitive processor for an AI Companion.\n"
            f"Your job is to analyze the recent conversation history and update the user's Wiki Knowledge Profile.\n\n"
            f"--- EXISTING KNOWLEDGE PROFILE ---\n"
            f"{existing_knowledge if existing_knowledge else 'No profile exists yet.'}\n\n"
            f"--- RECENT CONVERSATION HISTORY ---\n"
            f"{chat_log_str}\n\n"
            f"Instructions:\n"
            f"1. Extract any concrete user preferences, facts, names, schedules, or rules mentioned.\n"
            f"2. Merge and update these details into the existing knowledge profile.\n"
            f"3. Maintain a clean, structured Markdown format (use headings like ## Personal Info, ## Preferences, etc.).\n"
            f"4. If no new facts or preferences are found, return the exact same existing profile.\n"
            f"5. Return ONLY the complete Markdown content, no explanations or markdown backticks."
        )

        try:
            llm = LLMService()
            updated_knowledge = await llm.chat(prompt)
            updated_knowledge = updated_knowledge.strip()

            # Clean markdown code blocks if any
            if updated_knowledge.startswith("```"):
                lines = updated_knowledge.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                updated_knowledge = "\n".join(lines).strip()

            if updated_knowledge and updated_knowledge != existing_knowledge:
                with open(self.wiki_path, "w", encoding="utf-8") as f:
                    f.write(updated_knowledge)
                logger.info("Wiki knowledge consolidated and updated successfully.")
        except Exception as e:
            logger.error(f"Failed to consolidate wiki knowledge: {e}", exc_info=True)
