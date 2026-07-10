"""KnowledgeExtractor — trích xuất tri thức và sở thích từ tương tác.

Phân tích lịch sử trò chuyện hoặc kết quả tác vụ để đúc kết niềm tin mới về user hoặc hệ thống.
"""

from __future__ import annotations

import logging
import re
from typing import Dict

from belief.belief_store import belief_store

logger = logging.getLogger("ai-companion.learning.knowledge")


class KnowledgeExtractor:
    """Trích xuất tri thức và lưu trữ vào BeliefStore."""

    def __init__(self) -> None:
        pass

    def extract_from_text(self, text: str) -> Dict[str, str]:
        """Phân tích văn bản để tìm kiếm các tùy chọn/sở thích được chỉ rõ.

        Hỗ trợ nhận dạng một số mẫu câu thông dụng:
        - "Tớ thích dùng [Editor] để code" -> user preference
        - "Môi trường của tớ dùng [Tool]" -> env preference
        """
        extracted = {}
        if not text:
            return extracted

        # Regex tìm sở thích editor
        editor_match = re.search(r"thích dùng\s+([a-zA-Z0-9_\-\s]+)\s+để\s+code", text, re.IGNORECASE)
        if editor_match:
            editor = editor_match.group(1).strip()
            try:
                from belief.belief_updater import belief_updater
                belief_updater.register_evidence("user.preference.editor", editor, confidence=0.9, source="direct_feedback")
            except Exception:
                belief_store.set_belief("user.preference.editor", editor, confidence=0.9, source="direct_feedback")
            extracted["user.preference.editor"] = editor

        # Regex tìm sở thích theme màu
        theme_match = re.search(r"giao diện\s+([a-zA-Z0-9_\-\s]+)", text, re.IGNORECASE)
        if theme_match:
            theme = theme_match.group(1).strip()
            try:
                from belief.belief_updater import belief_updater
                belief_updater.register_evidence("user.preference.theme", theme, confidence=0.8, source="direct_feedback")
            except Exception:
                belief_store.set_belief("user.preference.theme", theme, confidence=0.8, source="direct_feedback")
            extracted["user.preference.theme"] = theme

        # Regex tìm đặc điểm cú đêm
        if any(k in text.lower() for k in ["code muộn", "ngủ muộn", "thức đêm"]):
            try:
                from belief.belief_updater import belief_updater
                belief_updater.register_evidence("user.trait.night_owl", "true", confidence=0.7, source="deduction")
            except Exception:
                belief_store.set_belief("user.trait.night_owl", "true", confidence=0.7, source="deduction")
            extracted["user.trait.night_owl"] = "true"

        if extracted:
            logger.info("KnowledgeExtractor successfully extracted %d facts from text", len(extracted))
            
        # Tích hợp cập nhật Đồ thị tri thức (Knowledge Graph)
        try:
            from knowledge.graph.graph_builder import graph_builder
            from knowledge.graph.knowledge_graph import knowledge_graph
            
            # 1. Build using parser patterns
            graph_builder.build_from_fact(text)
            
            # 2. Build structured relations from extracted dictionary
            for k, v in extracted.items():
                if k == "user.preference.editor":
                    knowledge_graph.add_relation("User", v, "PREFERS_EDITOR")
                elif k == "user.preference.theme":
                    knowledge_graph.add_relation("User", v, "PREFERS_THEME")
                elif k == "user.trait.night_owl":
                    knowledge_graph.add_relation("User", "night_owl", "HAS_TRAIT")
        except Exception as e:
            logger.warning("KnowledgeExtractor failed to build relation triplets: %s", e)
            
        return extracted


# Global singleton
knowledge_extractor = KnowledgeExtractor()
