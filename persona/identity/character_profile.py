"""Character profile dataclass — wraps YAML character config."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CharacterProfile:
    """Structured representation of a character's YAML configuration."""

    name: str
    description: str = ""
    personality: dict[str, float] = field(default_factory=dict)
    speech_style: list[str] = field(default_factory=list)
    favorite_topics: list[str] = field(default_factory=list)
    tts: dict[str, Any] = field(default_factory=dict)

    # ── Convenience accessors ──────────────────────────────────────────────

    def get_trait(self, trait: str, default: float = 0.5) -> float:
        """Return a personality trait value (0.0–1.0)."""
        return float(self.personality.get(trait, default))

    @property
    def is_cheerful(self) -> bool:
        return self.get_trait("cheerful") >= 0.7

    @property
    def is_curious(self) -> bool:
        return self.get_trait("curious") >= 0.7

    @property
    def is_shy(self) -> bool:
        return self.get_trait("shy") >= 0.6

    def tts_voice(self) -> str:
        return self.tts.get("voice", "vi-VN-HoaiMyNeural")

    def tts_kokoro_voice(self) -> str:
        return self.tts.get("kokoro_voice", "af_sarah")

    # ── Factory ────────────────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, data: dict) -> "CharacterProfile":
        """Build a CharacterProfile from raw YAML dict."""
        return cls(
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            personality={
                k: float(v)
                for k, v in data.get("personality", {}).items()
            },
            speech_style=list(data.get("speech_style", [])),
            favorite_topics=list(data.get("favorite_topics", [])),
            tts=dict(data.get("tts", {})),
        )

    @classmethod
    def default(cls) -> "CharacterProfile":
        """Fallback profile when YAML is missing."""
        return cls(
            name="IceGirl",
            description="AI Desktop Companion",
            personality={"cheerful": 0.9, "curious": 0.8, "friendly": 1.0, "shy": 0.3},
            speech_style=["cute", "playful"],
            favorite_topics=["AI", "Technology"],
            tts={"voice": "vi-VN-HoaiMyNeural"},
        )

    def __repr__(self) -> str:
        return f"<CharacterProfile name={self.name!r}>"
