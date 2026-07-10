from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class TaskPlanStep:
    id: str
    description: str
    status: str = "pending"  # pending | in_progress | done | failed


@dataclass
class TaskPlan:
    task_id: str
    steps: List[TaskPlanStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "steps": [
                {
                    "id": step.id,
                    "description": step.description,
                    "status": step.status
                }
                for step in self.steps
            ]
        }
