"""Integration tests for context and dependency components."""

from __future__ import annotations

import pytest
from perception.fusion.perception_fusion import PerceptionFusion
from runtime.dependency.dependency_graph import dependency_graph


def test_perception_fusion_integration() -> None:
    packet = PerceptionFusion.fuse(screen_text="Visual Studio Code editor open")
    assert packet.active_window == "VS Code editor"
    assert packet.activity == "coding"


def test_dependency_graph_integration() -> None:
    dependency_graph.add_module("ModuleB", ["ModuleA"])
    order = dependency_graph.resolve_order()
    assert "ModuleA" in order
    assert "ModuleB" in order
    assert order.index("ModuleA") < order.index("ModuleB")
