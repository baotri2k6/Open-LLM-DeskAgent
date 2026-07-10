"""Placeholder WebSocket manager.

The current MVP uses HTTP only so it can run with Python's standard library.
This class keeps the project boundary ready for a FastAPI/WebSocket upgrade.
"""

from __future__ import annotations

from typing import Any


class WebSocketManager:
    def __init__(self) -> None:
        self.clients: set[Any] = set()

    async def connect(self, websocket: Any) -> None:
        self.clients.add(websocket)

    async def disconnect(self, websocket: Any) -> None:
        self.clients.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead_clients = []
        for client in self.clients:
            try:
                await client.send_json(message)
            except Exception:
                dead_clients.append(client)
        for client in dead_clients:
            self.clients.discard(client)


websocket_manager = WebSocketManager()
