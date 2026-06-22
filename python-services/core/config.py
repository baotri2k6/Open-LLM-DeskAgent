"""Configuration helpers for the local Python service."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_CONFIG: dict[str, Any] = {
    "server": {"host": "127.0.0.1", "port": 8765},
    "app": {
        "name": "AI Companion Desktop 2.5D",
        "locale": "vi-VN",
        "avatarModel": "assets/live2d/IceGirl/IceGirl.model3.json",
        "interactionMode": "streamer",
    },
    "persona": {
        "name": "IceGirl",
        "language": "vi-VN",
        "style": "friendly",
    },
    "features": {
        "voice": False,
        "memory": True,
        "desktopControl": True,
        "screenAwareness": False,
        "documentRag": False,
        "twitchMode": False,
    },
    "twitch": {
        "channel": "",
    },
}


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class Config:
    def __init__(self) -> None:
        self.data = json.loads(json.dumps(DEFAULT_CONFIG))
        self._load_json("config/companion.config.json")
        persona = self._read_json("config/persona.config.json")
        if persona:
            self.data["persona"] = {**self.data.get("persona", {}), **persona}

        port = os.getenv("AI_COMPANION_PORT")
        if port:
            self.data.setdefault("server", {})["port"] = int(port)

    def _read_json(self, relative_path: str) -> dict[str, Any]:
        path = PROJECT_ROOT / relative_path
        if not path.exists() or path.stat().st_size == 0:
            return {}
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_json(self, relative_path: str) -> None:
        data = self._read_json(relative_path)
        if data:
            _deep_merge(self.data, data)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        current: Any = self.data
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def set(self, dotted_key: str, value: Any) -> None:
        parts = dotted_key.split(".")
        current = self.data
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

        # Save to file
        config_path = PROJECT_ROOT / "config" / "companion.config.json"
        try:
            if config_path.exists() and config_path.stat().st_size > 0:
                with config_path.open("r", encoding="utf-8") as handle:
                    file_data = json.load(handle)
            else:
                file_data = {}
            
            curr_file = file_data
            for part in parts[:-1]:
                if part not in curr_file or not isinstance(curr_file[part], dict):
                    curr_file[part] = {}
                curr_file = curr_file[part]
            curr_file[parts[-1]] = value
            
            with config_path.open("w", encoding="utf-8") as handle:
                json.dump(file_data, handle, indent=2, ensure_ascii=False)
        except Exception as err:
            print(f"[Config] Failed to save companion.config.json: {err}")

    @property
    def host(self) -> str:
        return str(self.get("server.host", "127.0.0.1"))

    @property
    def port(self) -> int:
        return int(self.get("server.port", 8765))


config = Config()
