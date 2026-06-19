"""Persona manager to load character configurations from YAML files."""

from __future__ import annotations

from pathlib import Path
import yaml

from core.config import PROJECT_ROOT


class PersonaManager:
    def __init__(self, characters_dir: Path | None = None) -> None:
        self.characters_dir = characters_dir or PROJECT_ROOT / "python-services" / "persona" / "characters"

    def load_persona(self, name: str) -> dict:
        """Loads a character persona configuration by name (YAML)."""
        filename = f"{name.lower()}.yaml"
        path = self.characters_dir / filename

        # Fallback to main project config/characters if not in python-services
        if not path.exists():
            alt_path = PROJECT_ROOT / "config" / "characters" / filename
            if alt_path.exists():
                path = alt_path

        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
