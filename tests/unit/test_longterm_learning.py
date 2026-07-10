"""Tests for KnowledgeDistiller and PatternLearner integration."""

from __future__ import annotations

import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock

from learning.experience.experience_store import experience_store
from learning.knowledge_distillation.knowledge_distiller import KnowledgeDistiller
from learning.pattern_learning.pattern_learner import PatternLearner
from cognition.prompts.prompt_builder import prompt_builder


@pytest.fixture
def temp_distilled_path(tmp_path) -> Path:
    return tmp_path / "distilled_knowledge.json"


@pytest.fixture
def temp_history_path(tmp_path) -> Path:
    return tmp_path / "activity_history.json"


def test_knowledge_distiller_flow(temp_distilled_path):
    # Setup mock experiences in experience_store
    experience_store.record_experience(
        goal_id="g1",
        goal_desc="Restoring Database Backup",
        is_successful=False,
        lessons_learned="Always check disk space before recovery"
    )
    experience_store.record_experience(
        goal_id="g2",
        goal_desc="Deploying Frontend App",
        is_successful=True,
        lessons_learned="Use npm run build for production production"
    )

    distiller = KnowledgeDistiller(path=temp_distilled_path)
    distiller.distill_experiences()

    facts = distiller.get_distilled_facts_for_prompt()
    assert len(facts) > 0
    assert any("Always check disk space before recovery" in f for f in facts)
    assert any("Use npm run build for production production" in f for f in facts)

    prompt_desc = distiller.describe_for_prompt()
    assert "[Distilled Lessons]" in prompt_desc
    assert "Always check disk space before recovery" in prompt_desc


def test_pattern_learner_flow(temp_history_path):
    learner = PatternLearner(path=temp_history_path)
    
    # Record some pattern data
    learner.record_activity(hour=9, activity="coding", app="VS Code")
    learner.record_activity(hour=9, activity="coding", app="VS Code")
    learner.record_activity(hour=9, activity="gaming", app="Steam")
    
    # Predict for hour 9
    probs = learner.predict_next_activity(current_hour=9)
    assert probs["coding"] == pytest.approx(2/3)
    assert probs["gaming"] == pytest.approx(1/3)
    
    # Highest probability activity
    label = learner.get_predicted_activity_label(current_hour=9)
    assert label == "coding"

    desc = learner.describe_for_prompt()
    assert "[Learned Habits]" in desc
    assert "coding" in desc


def test_prompt_builder_integration(temp_distilled_path, temp_history_path):
    experience_store.record_experience(
        goal_id="g1",
        goal_desc="Restoring Database Backup",
        is_successful=False,
        lessons_learned="Always check disk space before recovery"
    )
    distiller = KnowledgeDistiller(path=temp_distilled_path)
    distiller.distill_experiences()

    learner = PatternLearner(path=temp_history_path)
    learner.record_activity(hour=14, activity="coding", app="VS Code")
    learner.record_activity(hour=14, activity="coding", app="VS Code")

    # Mock the singleton instances to point to our test instances
    import sys
    import learning.knowledge_distillation.knowledge_distiller
    import learning.pattern_learning.pattern_learner
    
    kd_mod = sys.modules['learning.knowledge_distillation.knowledge_distiller']
    pl_mod = sys.modules['learning.pattern_learning.pattern_learner']
    
    orig_distiller = kd_mod.knowledge_distiller
    orig_learner = pl_mod.pattern_learner
    
    kd_mod.knowledge_distiller = distiller
    pl_mod.pattern_learner = learner

    try:
        # Construct system prompt
        prompt = prompt_builder.build()
        assert "[Distilled Lessons]" in prompt
    finally:
        # Restore original singletons
        kd_mod.knowledge_distiller = orig_distiller
        pl_mod.pattern_learner = orig_learner
