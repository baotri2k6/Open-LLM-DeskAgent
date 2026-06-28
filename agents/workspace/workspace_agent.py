"""Agent specialized in workspace management."""

from __future__ import annotations

from world.projects.project_context import project_context
from world.workspace.workspace_state import workspace_state


class WorkspaceAgent:
    """Provides workspace summaries for planners and coordinator agents."""

    name = "workspace"
    capabilities = ["workspace_snapshot", "project_context", "workspace_describe"]

    def snapshot(self, root: str | None = None) -> dict:
        return workspace_state.snapshot(root)

    def project_context(self, root: str | None = None) -> dict:
        return project_context.detect(root)

    def describe(self, root: str | None = None) -> str:
        return workspace_state.describe(root)

    async def run(self, task: str, **kwargs) -> dict:
        task_lower = task.lower()
        if "project" in task_lower:
            return {"success": True, "result": self.project_context(kwargs.get("root"))}
        if "describe" in task_lower or "summary" in task_lower:
            return {"success": True, "result": self.describe(kwargs.get("root"))}
        return {"success": True, "result": self.snapshot(kwargs.get("root"))}


workspace_agent = WorkspaceAgent()
