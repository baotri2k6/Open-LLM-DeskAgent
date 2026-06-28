"""Persona manager — loads and caches character configurations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from config.config import PROJECT_ROOT, RESOURCE_BASE, IS_FROZEN
from persona.identity.character_profile import CharacterProfile
from persona.behavior.personality import PersonalityProfile


class PersonaManager:
    """
    Loads character YAML files and returns structured CharacterProfile objects.
    Caches profiles in memory to avoid repeated disk reads.
    """

    def __init__(self, characters_dir: Optional[Path] = None) -> None:
        if characters_dir:
            self.characters_dir = Path(characters_dir)
        else:
            # Primary: flat project structure (Vision 3.0)
            self.characters_dir = PROJECT_ROOT / "persona" / "characters"

        self._cache: dict[str, CharacterProfile] = {}
        self.active_character = "icegirl"

    def get_system_prompt_section(self) -> str:
        """Sinh chuỗi system prompt biểu diễn thông tin Persona Core hiện tại."""
        profile = self.get_character_profile(self.active_character)
        traits_str = ", ".join(profile.personality.keys())
        speech_str = ", ".join(profile.speech_style)
        topics_str = ", ".join(profile.favorite_topics)
        
        return (
            f"[Persona Core]\n"
            f"Name: {profile.name}\n"
            f"Description: {profile.description}\n"
            f"Traits: {traits_str}\n"
            f"Speech Style: {speech_str}\n"
            f"Favorite Topics: {topics_str}"
        )

    def evolve_personality(self) -> None:
        """Tiến hóa tính cách dựa trên mối quan hệ và đặc điểm người dùng."""
        try:
            from persona.relationship.relationship_tracker import relationship_tracker
            from belief.user_model import user_model
            
            profile = self.get_character_profile(self.active_character)
            
            # 1. Tiến hóa speech style dựa trên perks của mối quan hệ
            perks = relationship_tracker.perks
            for perk in perks:
                if "Casual" in perk and "casual" not in profile.speech_style:
                    profile.speech_style.append("casual")
                if "Intimate" in perk and "intimate" not in profile.speech_style:
                    profile.speech_style.append("intimate")
                if "teasing" in perk.lower() and "teasing" not in profile.speech_style:
                    profile.speech_style.append("teasing")

            # 2. Tiến hóa chủ đề ưa thích dựa trên thói quen của user
            traits = user_model.get_user_traits()
            if "night_owl" in traits and "night owl hacks" not in profile.favorite_topics:
                profile.favorite_topics.append("night owl hacks")
                
            pref_editor = user_model.get_preference("editor")
            if pref_editor and f"{pref_editor} tips" not in profile.favorite_topics:
                profile.favorite_topics.append(f"{pref_editor} tips")
                
        except Exception:
            pass

    # ── Public API ─────────────────────────────────────────────────────────

    def load_persona(self, name: str) -> dict:
        """
        Load a character persona as a raw dict (backward-compatible).
        Returns empty dict if not found.
        """
        profile = self.get_character_profile(name)
        return {
            "name":           profile.name,
            "description":    profile.description,
            "personality":    profile.personality,
            "speech_style":   profile.speech_style,
            "favorite_topics": profile.favorite_topics,
            "tts":            profile.tts,
        }

    def get_character_profile(self, name: str) -> CharacterProfile:
        """
        Load and return a structured CharacterProfile.
        Uses cache if available; returns default if not found.
        """
        key = name.lower().strip()
        if key in self._cache:
            return self._cache[key]

        raw = self._load_yaml(key)
        if not raw:
            profile = CharacterProfile.default()
            self._cache[key] = profile
            return profile

        profile = CharacterProfile.from_yaml(raw)
        self._cache[key] = profile
        return profile

    def get_personality_profile(self, name: str) -> PersonalityProfile:
        """Return a PersonalityProfile built from the character's YAML."""
        character = self.get_character_profile(name)
        return PersonalityProfile.from_character_profile(character)

    def list_characters(self) -> list[str]:
        """Return available character names (without extension)."""
        if not self.characters_dir.exists():
            return []
        return [f.stem for f in self.characters_dir.glob("*.yaml")]

    def clear_cache(self) -> None:
        """Clear the in-memory profile cache."""
        self._cache.clear()

    # ── Internal ───────────────────────────────────────────────────────────

    def _load_yaml(self, name: str) -> dict:
        """Resolve YAML file path with fallbacks and return parsed dict."""
        filename = f"{name}.yaml"

        candidates = [
            self.characters_dir / filename,
        ]

        # Legacy fallbacks (old path structure)
        if IS_FROZEN:
            candidates += [
                RESOURCE_BASE / "api" / "persona" / "characters" / filename,
                RESOURCE_BASE / "config" / "characters" / filename,
            ]
        else:
            candidates += [
                PROJECT_ROOT / "api" / "persona" / "characters" / filename,
                PROJECT_ROOT / "config" / "characters" / filename,
            ]

        for path in candidates:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        return data if isinstance(data, dict) else {}
                except Exception:
                    continue

        return {}


# Global singleton
persona_manager = PersonaManager()

