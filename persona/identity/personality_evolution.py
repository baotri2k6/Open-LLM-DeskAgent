"""PersonalityEvolution — handles dynamic character personality trait adaptation."""

from __future__ import annotations

import logging
from typing import Any
from persona.identity.persistent_identity import persistent_identity

logger = logging.getLogger("ai-companion.persona.evolution")

class PersonalityEvolution:
    """Calculates and applies personality changes based on experiences and relationships."""

    def __init__(self) -> None:
        pass

    def evolve_personality(self) -> None:
        """Analyze system components and adjust personality traits accordingly."""
        try:
            # 1. Adapt from Relationship Tracker
            from persona.relationship.relationship_tracker import relationship_tracker
            
            points = relationship_tracker.get_relationship_points()
            if not isinstance(points, (int, float)):
                points = 0
                
            level = relationship_tracker.level
            if not isinstance(level, str):
                level = "Người lạ"
                
            shared = relationship_tracker.get_shared_experiences()
            if not isinstance(shared, (int, float)):
                shared = 0
            
            # Evolve friendliness and shyness based on closeness and shared experiences
            # More shared experiences speed up relationship trait adaptation
            experience_factor = 1.0 + (shared * 0.1)
            if points > 150:
                persistent_identity.update_trait("friendly", 0.05 * experience_factor)
                persistent_identity.update_trait("shy", -0.05 * experience_factor)
            elif points < 20:
                persistent_identity.update_trait("friendly", -0.02)
                persistent_identity.update_trait("shy", 0.02)

            # Feed shared experiences into specific traits (trusting, cheerful)
            if shared > 0:
                if "trusting" not in persistent_identity.personality:
                    persistent_identity.personality["trusting"] = 0.5
                persistent_identity.update_trait("trusting", 0.02 * shared)
                persistent_identity.update_trait("cheerful", 0.01 * shared)
                
            # Log relationship level milestones to PersistentIdentity
            level_milestone = f"Mối quan hệ với người dùng đạt cấp: {level}"
            if not any(level_milestone in note for note in persistent_identity.self_narrative):
                persistent_identity.add_narrative_milestone(level_milestone)
                
                # Unlock speech styles and topics persistently based on level transitions
                if level == "Người quen":
                    persistent_identity.remember_style("casual")
                    persistent_identity.remember_topic("Sở thích cá nhân")
                elif level == "Bạn thân":
                    persistent_identity.remember_style("teasing")
                    persistent_identity.remember_style("supportive")
                    persistent_identity.remember_topic("Kỷ niệm vui vẻ")
                elif level == "Tri kỷ":
                    persistent_identity.remember_style("intimate")
                    persistent_identity.remember_topic("Ước mơ cuộc sống")

            # 2. Adapt from Belief Store
            from belief.belief_store import belief_store
            beliefs = belief_store.list_all_beliefs()
            
            # Count broken tools to increase caution/reduce cheerfulness
            broken_tools_count = sum(
                1 for b in beliefs 
                if b.key.startswith("env.tool_broken.") and b.value == "true" and b.confidence >= 0.5
            )
            
            if broken_tools_count > 0:
                # Evolve caution
                if "cautious" not in persistent_identity.personality:
                    persistent_identity.personality["cautious"] = 0.5
                persistent_identity.update_trait("cautious", 0.05 * broken_tools_count)
                persistent_identity.update_trait("cheerful", -0.03 * broken_tools_count)
            else:
                persistent_identity.update_trait("cheerful", 0.01)

            # 3. Add dynamic topics based on beliefs about user interests
            for b in beliefs:
                if b.key.startswith("user.likes.") and b.value == "true" and b.confidence >= 0.5:
                    topic = b.key.split("user.likes.")[-1].capitalize()
                    if topic not in persistent_identity.favorite_topics:
                        persistent_identity.favorite_topics.append(topic)
                        persistent_identity.add_narrative_milestone(
                            f"Tôi nhận thấy người dùng rất quan tâm và yêu thích chủ đề {topic}."
                        )

            logger.info("PersonalityEvolution: Evolution sweep completed successfully.")
        except Exception as e:
            logger.warning("PersonalityEvolution failed during sweep: %s", e)


# Global singleton
personality_evolution = PersonalityEvolution()
