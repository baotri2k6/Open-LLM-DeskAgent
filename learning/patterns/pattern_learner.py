"""PatternLearner — learns recurring user activity and tool-use patterns."""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from config.config import WRITABLE_ROOT


@dataclass
class PatternPrediction:
    activity: str = "unknown"
    tool: str = ""
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PatternLearner:
    """Tracks time-of-day activities and tool usage to predict likely next behavior."""

    def __init__(self, patterns_path: Path | None = None) -> None:
        self._path = patterns_path or WRITABLE_ROOT / "data" / "learned_patterns.json"
        self.activity_by_hour: dict[str, Counter[str]] = {}
        self.tool_counts: Counter[str] = Counter()
        self.activity_counts: Counter[str] = Counter()
        self.transitions: Counter[str] = Counter()
        self._last_activity: str = ""
        self._load()

    def record_event(
        self,
        activity: str = "unknown",
        tool: str | None = None,
        timestamp: float | None = None,
        metadata: dict | None = None,
    ) -> None:
        timestamp = timestamp or time.time()
        hour = str(time.localtime(timestamp).tm_hour)
        activity = (activity or "unknown").strip()

        self.activity_counts[activity] += 1
        self.activity_by_hour.setdefault(hour, Counter())[activity] += 1

        if tool:
            self.tool_counts[tool.strip()] += 1

        if self._last_activity and self._last_activity != activity:
            self.transitions[f"{self._last_activity}->{activity}"] += 1
        self._last_activity = activity

        if metadata:
            meta_tool = metadata.get("tool") or metadata.get("tool_name")
            if meta_tool:
                self.tool_counts[str(meta_tool)] += 1

        self.save()

    def observe_experience(self, experience: Any) -> None:
        metadata = getattr(experience, "metadata", {}) or {}
        activity = metadata.get("activity") or self._infer_activity(str(getattr(experience, "goal_desc", "")))
        tool = metadata.get("tool") or metadata.get("tool_name")
        self.record_event(activity=activity, tool=tool, timestamp=getattr(experience, "timestamp", None), metadata=metadata)

    def predict_next(self, current_activity: str | None = None, hour: int | None = None) -> PatternPrediction:
        hour_key = str(hour if hour is not None else time.localtime().tm_hour)
        by_hour = self.activity_by_hour.get(hour_key, Counter())

        activity = ""
        reason = ""
        if current_activity:
            transition_prefix = f"{current_activity}->"
            candidates = {
                key.split("->", 1)[1]: count
                for key, count in self.transitions.items()
                if key.startswith(transition_prefix)
            }
            if candidates:
                activity, count = max(candidates.items(), key=lambda item: item[1])
                total = sum(candidates.values())
                confidence = count / max(1, total)
                reason = f"learned transition from {current_activity}"
            else:
                confidence = 0.0
        else:
            confidence = 0.0

        if not activity and by_hour:
            activity, count = by_hour.most_common(1)[0]
            confidence = count / max(1, sum(by_hour.values()))
            reason = f"common activity around hour {hour_key}"

        if not activity and self.activity_counts:
            activity, count = self.activity_counts.most_common(1)[0]
            confidence = count / max(1, sum(self.activity_counts.values()))
            reason = "most frequent activity overall"

        tool = self.tool_counts.most_common(1)[0][0] if self.tool_counts else ""
        return PatternPrediction(activity=activity or "unknown", tool=tool, confidence=round(confidence, 3), reason=reason)

    def describe_for_prompt(self) -> str:
        prediction = self.predict_next()
        if prediction.activity == "unknown" and not prediction.tool:
            return ""
        parts = [f"Likely next activity: {prediction.activity} ({prediction.confidence:.2f})"]
        if prediction.tool:
            parts.append(f"Common tool: {prediction.tool}")
        if prediction.reason:
            parts.append(f"Reason: {prediction.reason}")
        return "[Predicted User Patterns]\n" + "\n".join(f"- {p}" for p in parts)

    def snapshot(self) -> dict[str, Any]:
        return {
            "activity_by_hour": {hour: dict(counter) for hour, counter in self.activity_by_hour.items()},
            "tool_counts": dict(self.tool_counts),
            "activity_counts": dict(self.activity_counts),
            "transitions": dict(self.transitions),
            "last_activity": self._last_activity,
        }

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, ensure_ascii=False, indent=2)

    def _load(self) -> None:
        try:
            if not self._path.exists() or self._path.stat().st_size == 0:
                return
            with self._path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.activity_by_hour = {
                str(hour): Counter(values)
                for hour, values in data.get("activity_by_hour", {}).items()
            }
            self.tool_counts = Counter(data.get("tool_counts", {}))
            self.activity_counts = Counter(data.get("activity_counts", {}))
            self.transitions = Counter(data.get("transitions", {}))
            self._last_activity = str(data.get("last_activity", ""))
        except Exception:
            self.activity_by_hour = {}
            self.tool_counts = Counter()
            self.activity_counts = Counter()
            self.transitions = Counter()
            self._last_activity = ""

    def _infer_activity(self, text: str) -> str:
        lower = text.lower()
        if any(word in lower for word in ["code", "bug", "test", "build", "debug"]):
            return "coding"
        if any(word in lower for word in ["browser", "web", "search", "research"]):
            return "research"
        if any(word in lower for word in ["memory", "remember", "belief"]):
            return "memory"
        return "unknown"


pattern_learner = PatternLearner()
