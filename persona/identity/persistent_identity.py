"""Persistent identity — durable companion self model."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from config.config import WRITABLE_ROOT


@dataclass
class IdentitySnapshot:
    character_id: str = "icegirl"
    display_name: str = "IceGirl"
    continuity_notes: list[str] = field(default_factory=list)
    stable_traits: dict[str, float] = field(default_factory=dict)
    unlocked_styles: list[str] = field(default_factory=list)
    favorite_topics: list[str] = field(default_factory=list)
    shared_symbols: list[str] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


class PersistentIdentity:
    """Stores the durable parts of who the companion is becoming."""

    def __init__(self, identity_path: Path | None = None, filepath: Path | None = None) -> None:
        self._path = identity_path or filepath or WRITABLE_ROOT / "data" / "companion_identity.json"
        self._snapshot = self._load()

    @property
    def name(self) -> str:
        return self._snapshot.display_name

    @name.setter
    def name(self, value: str) -> None:
        self._snapshot.display_name = value

    @property
    def personality(self) -> dict[str, float]:
        if not self._snapshot.stable_traits:
            self._snapshot.stable_traits.update({
                "friendly": 1.0,
                "cheerful": 0.9,
                "curious": 0.8,
                "shy": 0.3,
            })
        return self._snapshot.stable_traits

    @property
    def favorite_topics(self) -> list[str]:
        return self._snapshot.favorite_topics

    @property
    def self_narrative(self) -> list[str]:
        return self._snapshot.continuity_notes

    @property
    def snapshot(self) -> IdentitySnapshot:
        return self._snapshot

    def to_dict(self) -> dict[str, Any]:
        return asdict(self._snapshot)

    def remember_style(self, style: str) -> None:
        style = style.strip()
        if style and style not in self._snapshot.unlocked_styles:
            self._snapshot.unlocked_styles.append(style)
            self._touch()

    def remember_topic(self, topic: str) -> None:
        topic = topic.strip()
        if topic and topic not in self._snapshot.favorite_topics:
            self._snapshot.favorite_topics.append(topic)
            self._touch()

    def remember_note(self, note: str) -> None:
        note = note.strip()
        if note and note not in self._snapshot.continuity_notes:
            self._snapshot.continuity_notes.append(note)
            self._snapshot.continuity_notes = self._snapshot.continuity_notes[-50:]
            self._touch()

    def add_narrative_milestone(self, note: str) -> None:
        self.remember_note(note)

    def update_trait(self, trait: str, delta: float) -> None:
        current = self.personality.get(trait, 0.5)
        self.personality[trait] = round(max(0.0, min(1.0, current + delta)), 3)
        self._touch()

    def merge_profile(self, character_id: str, display_name: str, traits: dict[str, float]) -> None:
        self._snapshot.character_id = character_id
        self._snapshot.display_name = display_name
        for key, value in traits.items():
            previous = self._snapshot.stable_traits.get(key, value)
            self._snapshot.stable_traits[key] = round((previous * 0.8) + (float(value) * 0.2), 3)
        self._touch()

    def apply_to_profile(self, profile: Any) -> Any:
        for style in self._snapshot.unlocked_styles:
            if style not in profile.speech_style:
                profile.speech_style.append(style)
        for topic in self._snapshot.favorite_topics:
            if topic not in profile.favorite_topics:
                profile.favorite_topics.append(topic)
        for trait, value in self._snapshot.stable_traits.items():
            profile.personality.setdefault(trait, value)
        return profile

    def _touch(self) -> None:
        self._snapshot.updated_at = time.time()
        self.save()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)

    def _load(self) -> IdentitySnapshot:
        try:
            if self._path.exists() and self._path.stat().st_size > 0:
                with self._path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                return IdentitySnapshot(
                    character_id=data.get("character_id", "icegirl"),
                    display_name=data.get("display_name", "IceGirl"),
                    continuity_notes=list(data.get("continuity_notes", [])),
                    stable_traits={k: float(v) for k, v in data.get("stable_traits", {}).items()},
                    unlocked_styles=list(data.get("unlocked_styles", [])),
                    favorite_topics=list(data.get("favorite_topics", [])),
                    shared_symbols=list(data.get("shared_symbols", [])),
                    updated_at=float(data.get("updated_at", time.time())),
                )
        except Exception:
            pass
        return IdentitySnapshot()


persistent_identity = PersistentIdentity()
