"""Unit tests for core helper components."""

from __future__ import annotations

import pytest
from persona.emotion.emotion_detector import emotion_detector
from knowledge.wiki.wiki_loader import wiki_loader


def test_emotion_detector() -> None:
    assert emotion_detector.detect_emotion("Tớ rất vui hôm nay") == "happy"
    assert emotion_detector.detect_emotion("Buồn quá đi mất") == "sad"
    assert emotion_detector.detect_emotion("Bình thường") == "neutral"


def test_wiki_loader_offline() -> None:
    # Ensure it handles connection errors gracefully
    res = wiki_loader.fetch_summary("NonExistentTopicUnique12345")
    assert res is None
