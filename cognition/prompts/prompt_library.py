"""Library of structured prompt templates."""

from __future__ import annotations


class PromptLibrary:
    """Library of structured prompt templates for companion intelligence."""

    SYSTEM_BASE = (
        "Bạn là IceGirl, một nữ trợ lý ảo cá nhân đáng yêu, năng động và luôn đồng hành bên cạnh người dùng."
    )

    MONOLOGUE_TEMPLATE = (
        "Dưới đây là bối cảnh hiện tại: {context_str}\n"
        "Hãy suy nghĩ ngắn gọn (dưới 3 câu) về những gì bạn muốn nói hoặc làm tiếp theo."
    )

    COMPACTION_TEMPLATE = (
        "Hãy tóm tắt cuộc trò chuyện hiện tại dưới 150 từ làm thông tin nền cho các lượt trò chuyện sau."
    )

    @classmethod
    def get_prompt(cls, key: str, default: str = "") -> str:
        """Get prompt template by key."""
        return getattr(cls, key.upper(), default)
