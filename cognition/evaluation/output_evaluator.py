"""OutputEvaluator — đánh giá chất lượng phản hồi từ LLM.

Kiểm tra độ trùng lặp (repetition), câu trả lời rỗng, hoặc các định dạng lỗi để yêu cầu sinh lại nếu cần.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("ai-companion.cognition.evaluation")


@dataclass
class EvaluationResult:
    """Kết quả đánh giá chất lượng."""
    is_acceptable: bool = True
    score:         float = 1.0  # 0.0 -> 1.0
    reason:        str = ""


class OutputEvaluator:
    """Đánh giá chất lượng của văn bản đầu ra từ LLM."""

    def evaluate(self, text: str) -> EvaluationResult:
        """Đánh giá chất lượng văn bản.

        Args:
            text: Văn bản cần đánh giá.
        """
        text = text.strip()
        if not text:
            return EvaluationResult(is_acceptable=False, score=0.0, reason="Phản hồi rỗng")

        # 1. Phát hiện lặp từ hoặc câu nghiêm trọng (bệnh thường gặp của LLM nhỏ)
        words = text.split()
        if len(words) > 10:
            # Kiểm tra tỷ lệ từ độc nhất (unique words ratio)
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                return EvaluationResult(
                    is_acceptable=False,
                    score=unique_ratio,
                    reason=f"Tỷ lệ lặp từ quá cao ({1.0 - unique_ratio:.1%})"
                )

        # 2. Phát hiện lỗi lặp ký tự (ví dụ "aaaaaaaaa")
        for word in words:
            if len(word) > 15:
                # Tìm chuỗi ký tự lặp liên tiếp
                for char in set(word):
                    if char * 6 in word:
                        return EvaluationResult(
                            is_acceptable=False,
                            score=0.2,
                            reason=f"Lặp ký tự liên tiếp trong từ '{word}'"
                        )

        # 3. Phản hồi quá ngắn không tự nhiên (chỉ có 1 ký tự đặc biệt)
        if len(text) == 1 and not text.isalnum():
            return EvaluationResult(is_acceptable=False, score=0.1, reason="Chỉ chứa ký tự đặc biệt")

        return EvaluationResult(is_acceptable=True, score=1.0)


# Global singleton
output_evaluator = OutputEvaluator()
