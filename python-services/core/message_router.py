"""Message router connecting HTTP requests to the planner agent."""

from __future__ import annotations

from typing import Any

from agents.planner_agent import PlannerAgent


class MessageRouter:
    def __init__(self, planner: PlannerAgent | None = None) -> None:
        self.planner = planner or PlannerAgent()

    async def route(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text", "")).strip()
        if not text:
            return {
                "type": "error",
                "code": "empty_message",
                "message": "Tin nhắn đang trống.",
            }

        response = await self.planner.handle_message(text, payload.get("context", {}))
        response.setdefault("id", payload.get("id", "assistant_response"))
        return response
