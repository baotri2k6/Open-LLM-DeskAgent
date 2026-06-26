"""Personality profile — structured accessor for character personality traits."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from persona.identity.character_profile import CharacterProfile


# ── Trait categories ──────────────────────────────────────────────────────────

POSITIVE_TRAITS  = {"cheerful", "friendly", "curious", "confident", "energetic"}
NEGATIVE_TRAITS  = {"shy", "anxious", "serious", "reserved"}
SOCIAL_TRAITS    = {"friendly", "cheerful", "curious"}


@dataclass
class PersonalityProfile:
    """
    Structured personality accessor built from a CharacterProfile.
    Provides computed properties and interaction-ready descriptions.
    """

    name: str
    traits: dict[str, float] = field(default_factory=dict)
    speech_style: list[str]  = field(default_factory=list)
    favorite_topics: list[str] = field(default_factory=list)

    # ── Computed properties ────────────────────────────────────────────────

    @property
    def energy_level(self) -> float:
        """Estimated base energy level from personality traits."""
        return (
            self.get("cheerful", 0.5) * 0.4
            + self.get("curious",  0.5) * 0.3
            + self.get("friendly", 0.5) * 0.3
        )

    @property
    def social_warmth(self) -> float:
        """How warm/open the character is socially."""
        return (self.get("friendly", 0.5) + self.get("cheerful", 0.5)) / 2

    @property
    def curiosity_base(self) -> float:
        """Baseline curiosity trait value."""
        return self.get("curious", 0.5)

    @property
    def is_outgoing(self) -> bool:
        return self.social_warmth >= 0.7

    @property
    def speech_descriptors(self) -> str:
        """Comma-joined speech style description."""
        return ", ".join(self.speech_style) if self.speech_style else "friendly"

    # ── Accessor ───────────────────────────────────────────────────────────

    def get(self, trait: str, default: float = 0.5) -> float:
        return float(self.traits.get(trait, default))

    def summary(self) -> str:
        """One-line personality summary for system prompt injection."""
        top = sorted(self.traits.items(), key=lambda x: x[1], reverse=True)[:3]
        top_str = ", ".join(f"{k}={v:.1f}" for k, v in top)
        return f"{self.name}: [{top_str}] style=[{self.speech_descriptors}]"

    # ── Factory ────────────────────────────────────────────────────────────

    @classmethod
    def from_character_profile(cls, profile: "CharacterProfile") -> "PersonalityProfile":
        return cls(
            name=profile.name,
            traits=dict(profile.personality),
            speech_style=list(profile.speech_style),
            favorite_topics=list(profile.favorite_topics),
        )

    @classmethod
    def default(cls) -> "PersonalityProfile":
        return cls(
            name="IceGirl",
            traits={"cheerful": 0.9, "curious": 0.8, "friendly": 1.0, "shy": 0.3},
            speech_style=["cute", "playful", "teasing"],
            favorite_topics=["AI", "Technology", "Games"],
        )
