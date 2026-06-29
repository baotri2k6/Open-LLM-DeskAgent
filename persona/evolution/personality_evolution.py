"""Personality evolution engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from persona.identity.persistent_identity import PersistentIdentity, persistent_identity


@dataclass
class EvolutionResult:
    changed: bool
    added_styles: list[str] = field(default_factory=list)
    added_topics: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed": self.changed,
            "added_styles": self.added_styles,
            "added_topics": self.added_topics,
            "notes": self.notes,
        }


class PersonalityEvolution:
    """Applies bounded, persistent personality growth to a character profile."""

    def __init__(self, identity: PersistentIdentity | None = None) -> None:
        self.identity = identity or persistent_identity

    def evolve(self, profile: Any, relationship: Any | None = None, user_model: Any | None = None) -> EvolutionResult:
        added_styles: list[str] = []
        added_topics: list[str] = []
        notes: list[str] = []

        self.identity.merge_profile(
            character_id=getattr(profile, "name", "icegirl").lower(),
            display_name=getattr(profile, "name", "IceGirl"),
            traits=getattr(profile, "personality", {}),
        )

        perks = list(getattr(relationship, "perks", []) or [])
        for perk in perks:
            lowered = perk.lower()
            if "casual" in lowered:
                self._add_style(profile, "casual", added_styles)
            if "intimate" in lowered:
                self._add_style(profile, "intimate", added_styles)
            if "teasing" in lowered:
                self._add_style(profile, "teasing", added_styles)
            if "trust" in lowered:
                self._add_style(profile, "supportive", added_styles)

        if relationship is not None:
            level = getattr(relationship, "level", "")
            shared = 0
            try:
                shared = relationship.get_shared_experiences()
            except Exception:
                shared = 0
            if level:
                note = f"Relationship level with user: {level}"
                self.identity.remember_note(note)
                notes.append(note)
            if shared >= 3:
                self._add_topic(profile, "shared project memories", added_topics)

        traits = []
        if user_model is not None:
            try:
                traits = user_model.get_user_traits()
            except Exception:
                traits = []

            if "night_owl" in traits:
                self._add_topic(profile, "night owl hacks", added_topics)
            if "hardworking" in traits:
                self._add_style(profile, "encouraging", added_styles)

            for pref_key in ("editor", "language", "stack"):
                try:
                    pref = user_model.get_preference(pref_key)
                except Exception:
                    pref = ""
                if pref:
                    self._add_topic(profile, f"{pref} tips", added_topics)

        self.identity.apply_to_profile(profile)
        changed = bool(added_styles or added_topics or notes)
        return EvolutionResult(changed=changed, added_styles=added_styles, added_topics=added_topics, notes=notes)

    def _add_style(self, profile: Any, style: str, added: list[str]) -> None:
        if style not in profile.speech_style:
            profile.speech_style.append(style)
            added.append(style)
        self.identity.remember_style(style)

    def _add_topic(self, profile: Any, topic: str, added: list[str]) -> None:
        if topic not in profile.favorite_topics:
            profile.favorite_topics.append(topic)
            added.append(topic)
        self.identity.remember_topic(topic)


personality_evolution = PersonalityEvolution()
