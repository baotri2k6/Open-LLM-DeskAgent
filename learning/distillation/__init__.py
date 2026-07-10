"""learning.distillation package."""

from learning.distillation.knowledge_distiller import KnowledgeDistiller, knowledge_distiller
from learning.distillation.skill_distiller import SkillDistiller, skill_distiller

__all__ = ["KnowledgeDistiller", "knowledge_distiller", "SkillDistiller", "skill_distiller"]
