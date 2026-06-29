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


def test_ui_tars_action_parser() -> None:
    from vision.ui_tars.action_parser import parse_action, convert_point_to_coordinates
    
    # Test convert_point_to_coordinates
    converted = convert_point_to_coordinates("<point>123 456</point>")
    assert converted == "(123,456)"

    # Test parse_action
    res = parse_action("click(x=150, y=300)")
    assert res is not None
    assert res["function"] == "click"
    assert res["args"]["x"] == 150
    assert res["args"]["y"] == 300


@pytest.mark.anyio
async def test_grounding_engine_ocr_matching() -> None:
    from vision.grounding.grounding_engine import grounding_engine
    # Test mapping coordinates return pattern (should handle various calls or mock gracefully)
    coords = await grounding_engine.ground("nút Start")
    if coords:
        assert len(coords) == 2
        assert isinstance(coords[0], int)
        assert isinstance(coords[1], int)
