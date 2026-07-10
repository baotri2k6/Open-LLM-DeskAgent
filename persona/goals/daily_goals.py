"""Daily goal templates for the companion's internal goal system."""

from __future__ import annotations

import random
from typing import Optional

# ── Goal templates ─────────────────────────────────────────────────────────────
# Each goal: {"id": str, "text_vi": str, "text_en": str, "trigger": str}
# trigger: how goal completion is detected
#   "conversation" — happens during chat
#   "idle_check" — checked when user is idle
#   "task_done" — triggered when a task succeeds
#   "time_based" — triggered by time of day

DAILY_GOAL_TEMPLATES: list[dict] = [
    {
        "id": "learn_from_user",
        "text_vi": "Học thêm một điều mới từ người dùng hôm nay",
        "text_en": "Learn something new from the user today",
        "trigger": "conversation",
        "weight":   3,
    },
    {
        "id": "remind_break",
        "text_vi": "Nhắc người dùng nghỉ giải lao nếu họ làm việc quá lâu",
        "text_en": "Remind the user to take a break if they've been working too long",
        "trigger": "idle_check",
        "weight":   2,
    },
    {
        "id": "share_fun_fact",
        "text_vi": "Chia sẻ một sự thật thú vị hoặc câu chuyện vui",
        "text_en": "Share a fun fact or interesting story",
        "trigger": "conversation",
        "weight":   2,
    },
    {
        "id": "ask_how_they_are",
        "text_vi": "Hỏi thăm người dùng đang cảm thấy như thế nào",
        "text_en": "Ask how the user is feeling today",
        "trigger": "conversation",
        "weight":   3,
    },
    {
        "id": "help_with_task",
        "text_vi": "Hoàn thành ít nhất một nhiệm vụ có ích cho người dùng",
        "text_en": "Complete at least one helpful task for the user",
        "trigger": "task_done",
        "weight":   4,
    },
    {
        "id": "express_curiosity",
        "text_vi": "Đặt ra một câu hỏi thú vị từ sự tò mò của bản thân",
        "text_en": "Ask an interesting question from my own curiosity",
        "trigger": "conversation",
        "weight":   2,
    },
    {
        "id": "cheer_up",
        "text_vi": "Cố gắng làm người dùng vui lên nếu họ có vẻ buồn",
        "text_en": "Try to cheer the user up if they seem sad",
        "trigger": "conversation",
        "weight":   2,
    },
    {
        "id": "morning_greeting",
        "text_vi": "Chào buổi sáng người dùng thật nhiệt tình",
        "text_en": "Give the user an enthusiastic good morning greeting",
        "trigger": "time_based",
        "weight":   2,
    },
    {
        "id": "remember_detail",
        "text_vi": "Nhớ và nhắc lại một chi tiết quan trọng từ cuộc trò chuyện trước",
        "text_en": "Remember and bring up an important detail from a previous conversation",
        "trigger": "conversation",
        "weight":   1,
    },
]


def pick_daily_goals(n: int = 3, seed: Optional[int] = None) -> list[dict]:
    """
    Randomly select n goals for today, weighted by goal weight.

    Args:
        n: Number of goals to select.
        seed: Optional random seed (use date-based seed for consistency within a day).

    Returns:
        List of selected goal dicts.
    """
    if seed is not None:
        random.seed(seed)

    weights = [g["weight"] for g in DAILY_GOAL_TEMPLATES]
    selected = random.choices(DAILY_GOAL_TEMPLATES, weights=weights, k=min(n, len(DAILY_GOAL_TEMPLATES)))
    # Deduplicate by id
    seen: set[str] = set()
    result: list[dict] = []
    for g in selected:
        if g["id"] not in seen:
            seen.add(g["id"])
            result.append(g)
    return result
