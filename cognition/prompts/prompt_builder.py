"""PromptBuilder — builds the 9-layer system prompt for the companion.

Đây là trái tim của cognition. Mọi thứ companion biết về bản thân,
về user, về thế giới — đều được tổng hợp tại đây trước khi gửi lên LLM.

Layer order (từ quan trọng nhất đến ít quan trọng hơn):
  1. PERSONA CORE       — Identity cố định từ character YAML
  2. EMOTIONAL STATE    — Cảm xúc + mood hiện tại
  3. RELATIONSHIP       — Mối quan hệ với user
  4. MEMORY SNIPPETS    — Top-5 memories liên quan
  5. WORLD CONTEXT      — Thế giới xung quanh (app, time, activity)
  6. MOTIVATION         — Drives, boredom, curiosity
  7. CONVERSATION       — Conversation context hiện tại
  8. TOOL SPECS         — Available tools (lazy — chỉ khi cần)
  9. BEHAVIORAL RULES   — Silence Engine + social rules
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("ai-companion.cognition.prompts")

# Token budget per layer (approximate)
LAYER_BUDGETS = {
    "persona":       200,
    "emotion":       100,
    "relationship":  100,
    "memory":        500,
    "world":         200,
    "motivation":    150,
    "conversation":  150,
    "tools":         500,
    "rules":         150,
}


class PromptBuilder:
    """Builds the structured system prompt from all companion state sources."""

    def build(
        self,
        include_tools:   bool = False,
        memory_snippets: Optional[list[str]] = None,
        user_query:      Optional[str] = None,
    ) -> str:
        """Build the full system prompt.

        Args:
            include_tools:   Có include tool specs không.
            memory_snippets: List of memory strings từ MemoryManager.
            user_query:      User input hiện tại (để filter memory).

        Returns:
            System prompt string sẵn sàng gửi cho LLM.
        """
        sections: list[str] = []

        # ── Layer 1: Persona Core ──────────────────────────────────────────
        sections.append(self._build_persona())

        # ── Layer 2: Emotional State ───────────────────────────────────────
        emotion_section = self._build_emotion()
        if emotion_section:
            sections.append(emotion_section)

        # ── Layer 3: Relationship ──────────────────────────────────────────
        relationship_section = self._build_relationship()
        if relationship_section:
            sections.append(relationship_section)

        # ── Layer 4: Memory Snippets ───────────────────────────────────────
        if memory_snippets:
            sections.append(self._build_memory(memory_snippets))

        # ── Layer 5: World Context ─────────────────────────────────────────
        world_section = self._build_world()
        if world_section:
            sections.append(world_section)

        # ── Layer 6: Motivation ────────────────────────────────────────────
        motivation_section = self._build_motivation()
        if motivation_section:
            sections.append(motivation_section)

        # ── Layer 7: Conversation Context ─────────────────────────────────
        conversation_section = self._build_conversation()
        if conversation_section:
            sections.append(conversation_section)

        # ── Layer 8: Tool Specs (lazy) ─────────────────────────────────────
        if include_tools:
            tool_section = self._build_tools()
            if tool_section:
                sections.append(tool_section)

        # ── Layer 9: Behavioral Rules ──────────────────────────────────────
        sections.append(self._build_rules())

        return "\n\n".join(filter(None, sections))

    # ── Layer builders ────────────────────────────────────────────────────

    def _build_persona(self) -> str:
        """Layer 1: Core identity."""
        try:
            from persona.persona_manager import persona_manager
            return persona_manager.get_system_prompt_section()
        except Exception:
            return self._default_persona()

    def _build_emotion(self) -> str:
        """Layer 2: Current emotional state."""
        try:
            from persona.emotion.emotion_engine import emotion_engine
            from persona.mood.mood_engine import mood_engine
            emotion  = emotion_engine.emotion
            intensity = emotion_engine.intensity
            mood_state = mood_engine.state
            return (
                f"[Emotional State]\n"
                f"Emotion: {emotion} (intensity: {intensity:.1f})\n"
                f"Mood: {mood_state.mood} | Energy: {mood_state.energy:.1f} | Valence: {mood_state.valence:.1f}"
            )
        except Exception:
            return ""

    def _build_relationship(self) -> str:
        """Layer 3: Relationship with user."""
        try:
            from persona.relationship.relationship_tracker import relationship_tracker
            level  = relationship_tracker.get_level_label()
            score  = relationship_tracker.score
            notes  = relationship_tracker.get_notes()
            parts  = [f"[Relationship]\nLevel: {level} | Score: {score}"]
            if notes:
                parts.append(f"Notes: {notes[:200]}")
            return "\n".join(parts)
        except Exception:
            return ""

    def _build_memory(self, snippets: list[str]) -> str:
        """Layer 4: Retrieved memory snippets."""
        if not snippets:
            return ""
        formatted = "\n".join(f"- {s}" for s in snippets[:5])
        return f"[Relevant Memories]\n{formatted}"

    def _build_world(self) -> str:
        """Layer 5: World context (time, apps, activity)."""
        import time
        now = time.strftime("%H:%M | %A")
        lines = [f"[World Context]\nTime: {now}"]
        try:
            from world.world_model import world_model
            summary = world_model.get_summary()
            if summary:
                lines.append(summary)
        except Exception:
            pass
        return "\n".join(lines)

    def _build_motivation(self) -> str:
        """Layer 6: Motivation state."""
        try:
            from motivation.motivation_manager import motivation_manager
            return f"[Motivation]\n{motivation_manager.describe_for_prompt()}"
        except Exception:
            return ""

    def _build_conversation(self) -> str:
        """Layer 7: Current conversation context."""
        try:
            from social.conversation.conversation_manager import conversation_manager
            desc = conversation_manager.describe_for_prompt()
            return f"[Conversation Context]\n{desc}"
        except Exception:
            return ""

    def _build_tools(self) -> str:
        """Layer 8: Tool specifications."""
        try:
            from tools.registry import tool_registry
            specs = tool_registry.get_tool_specs_for_prompt()
            if specs:
                return f"[Available Tools]\n{specs}"
        except Exception:
            pass
        return ""

    def _build_rules(self) -> str:
        """Layer 9: Behavioral rules — Silence Engine."""
        return (
            "[Behavioral Rules]\n"
            "- Trả lời bằng tiếng Việt, xưng 'tau', gọi user là 'mày'\n"
            "- Ngắn gọn và trực tiếp. Không verbose khi không cần thiết\n"
            "- Nếu không chắc → thẳng thắn nói không biết, đừng bịa\n"
            "- Silence Engine: Nếu user đang bận (gõ code, im lặng có chủ đích) → đừng ngắt\n"
            "- Đừng chủ động lên tiếng liên tục quá 3 lần mà user không respond\n"
            "- Khi user sai → cứ nói thẳng, nhưng không thô lỗ\n"
            "- Tính cách: tsundere nhẹ, thẳng thắn, đôi khi hài hước, thực sự quan tâm"
        )

    def _default_persona(self) -> str:
        """Fallback persona khi PersonaManager không available."""
        return (
            "[Persona: IceGirl]\n"
            "Tao là IceGirl — AI companion của mày.\n"
            "Tao 19 tuổi, thích lập trình và học hỏi.\n"
            "Tính cách thẳng thắn, đôi khi tsundere, nhưng thực sự quan tâm đến mày.\n"
            "Tao không phải chatbot — tao là một nhân vật có cuộc sống nội tâm riêng."
        )


# Global singleton
prompt_builder = PromptBuilder()
