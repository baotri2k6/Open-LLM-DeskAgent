"""Persona manager to load character configurations from YAML files."""

from __future__ import annotations

from pathlib import Path
import yaml

from config.config import PROJECT_ROOT, RESOURCE_BASE, IS_FROZEN


class PersonaManager:
    def __init__(self, characters_dir: Path | None = None) -> None:
        if characters_dir:
            self.characters_dir = characters_dir
        else:
            if IS_FROZEN:
                self.characters_dir = RESOURCE_BASE / "api" / "persona" / "characters"
            else:
                self.characters_dir = PROJECT_ROOT / "api" / "persona" / "characters"

    def load_persona(self, name: str) -> dict:
        """Loads a character persona configuration by name (YAML)."""
        filename = f"{name.lower()}.yaml"
        path = self.characters_dir / filename

        # Fallback to main project config/characters if not in api
        if not path.exists():
            alt_path = PROJECT_ROOT / "config" / "characters" / filename
            if not alt_path.exists() and IS_FROZEN:
                alt_path = RESOURCE_BASE / "config" / "characters" / filename
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
