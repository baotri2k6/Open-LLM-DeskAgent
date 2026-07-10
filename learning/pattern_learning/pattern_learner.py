"""PatternLearner — học hỏi thói quen hoạt động theo thời gian của người dùng."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ai-companion.learning.pattern_learning")


try:
    from config.config import WRITABLE_ROOT
    _HISTORY_PATH = WRITABLE_ROOT / "data" / "activity_history.json"
except Exception:
    _HISTORY_PATH = Path("data") / "activity_history.json"


class PatternLearner:
    """Học và dự đoán thói quen hoạt động của người dùng."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _HISTORY_PATH
        self._history: List[dict] = []
        self._load()

    def record_activity(self, hour: int, activity: str, app: str | None = None) -> None:
        """Ghi nhận hoạt động hiện tại để phân tích thói quen."""
        if not activity or activity == "unknown":
            return

        record = {
            "hour": hour,
            "activity": activity,
            "app": app or "unknown",
            "timestamp": time.time()
        }
        self._history.append(record)

        # Giới hạn kích thước lịch sử để tránh phình tệp
        if len(self._history) > 200:
            self._history = self._history[-200:]

        self._save()
        logger.debug("PatternLearner: Recorded activity '%s' at hour %d", activity, hour)

    def predict_next_activity(self, current_hour: int) -> Dict[str, float]:
        """Dự đoán phân phối xác suất các hoạt động khả dĩ của người dùng cho khung giờ hiện tại."""
        if not self._history:
            return {}

        # Lọc lịch sử trong khung giờ lân cận (+/- 1 giờ) để tạo tập mẫu tin cậy
        sample_activities = []
        for r in self._history:
            h = r.get("hour")
            if h is not None:
                # Tính khoảng cách giờ trên vòng tròn 24h
                diff = abs(h - current_hour)
                if diff > 12:
                    diff = 24 - diff
                
                # Trọng số lân cận
                if diff <= 1:
                    sample_activities.append(r.get("activity"))

        if not sample_activities:
            # Fallback về toàn bộ lịch sử nếu không có mẫu trong khung giờ lân cận
            sample_activities = [r.get("activity") for r in self._history]

        # Tính toán xác suất
        counts: Dict[str, int] = {}
        for act in sample_activities:
            if act:
                counts[act] = counts.get(act, 0) + 1

        total = sum(counts.values())
        if total == 0:
            return {}

        return {act: count / total for act, count in counts.items()}

    def get_predicted_activity_label(self, current_hour: int) -> Optional[str]:
        """Lấy nhãn hoạt động có xác suất xuất hiện cao nhất."""
        probs = self.predict_next_activity(current_hour)
        if not probs:
            return None
        return max(probs, key=probs.get)  # type: ignore

    def describe_for_prompt(self) -> str:
        """Mô tả thói quen người dùng đã học được cho system prompt."""
        current_hour = time.localtime().tm_hour
        probs = self.predict_next_activity(current_hour)
        if not probs:
            return ""
        predicted = max(probs, key=probs.get) # type: ignore
        conf = probs[predicted]
        if conf >= 0.4:
            return f"[Learned Habits]\nUser thường hoạt động ở khung giờ này với thói quen: {predicted} (độ tin cậy: {conf*100:.0f}%)"
        return ""

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save activity history: %s", e)

    def _load(self) -> None:
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
        except Exception as e:
            logger.error("Failed to load activity history: %s", e)
            self._history = []


# Global singleton
pattern_learner = PatternLearner()
