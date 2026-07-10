"""Unit tests for Jarvis Core features: system telemetry and hotword wake triggers."""

from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock, patch

from life.observe.observer import life_observer, LifeContext
from life.decide.decision_engine import decision_engine
from life.think.thinker import thinker
from speech.hotword.hotword_detector import HotwordDetector


def test_observer_collects_hardware_telemetry():
    context = life_observer.observe()
    assert hasattr(context, "cpu_usage")
    assert hasattr(context, "ram_usage")
    assert hasattr(context, "disk_usage")
    assert isinstance(context.cpu_usage, float)
    assert isinstance(context.ram_usage, float)
    assert isinstance(context.disk_usage, float)
    assert context.cpu_usage >= 0.0
    assert context.ram_usage >= 0.0
    assert context.disk_usage >= 0.0


def test_decision_engine_hardware_alert_bypass():
    context = LifeContext(
        cpu_usage=90.0,
        ram_usage=45.0,
        disk_usage=20.0
    )
    
    # Enable cooldown to verify alert bypasses it
    decision_engine._last_proactive_time = time.time()
    
    decision = decision_engine.decide(context)
    assert decision.should_act is True
    assert decision.action_type == "proactive_hardware_alert_cpu"
    assert "CPU đang quá tải" in decision.message_hint


def test_thinker_hardware_alert_thoughts():
    context = LifeContext(
        cpu_usage=12.0,
        ram_usage=95.0,
        disk_usage=30.0
    )
    
    res = thinker.think(context)
    assert "Cảnh báo hệ thống" in res["thought"]
    assert "RAM" in res["thought"]
    assert res["proposed_intention"] == "hardware_alert_ram"
    assert res["stay_silent"] is False # Alerts must break silence


@patch("speech.stt.stt_service.STTService")
def test_hotword_detector_flow(mock_stt_class):
    # Mock STT instance
    mock_stt = MagicMock()
    mock_stt.available = True
    async def mock_transcribe_bytes(*args, **kwargs):
        return {"success": True, "text": "Hello IceGirl how are you"}
    mock_stt.transcribe_bytes = mock_transcribe_bytes
    mock_stt_class.return_value = mock_stt

    wake_triggered = False
    def on_wake():
        nonlocal wake_triggered
        wake_triggered = True

    detector = HotwordDetector(
        wake_words=["icegirl"],
        on_wake=on_wake
    )

    # Test raw pcm wav processing triggers wake word matching
    detector._transcribe_and_check(b"fake wav bytes")
    assert wake_triggered is True
