"""Workspace state snapshot."""

from __future__ import annotations

from pathlib import Path

from config.config import PROJECT_ROOT
from world.projects.project_context import project_context


class WorkspaceState:
    """Summarizes the current repository/workspace without heavy scanning."""

    def snapshot(self, root: str | Path | None = None) -> dict:
        workspace = Path(root or PROJECT_ROOT).resolve()
        project = project_context.detect(workspace)
        try:
            top_level = sorted(item.name for item in workspace.iterdir() if not item.name.startswith("."))
        except Exception:
            top_level = []

        return {
            "root": str(workspace),
            "project": project,
            "top_level": top_level[:50],
        }

    def describe(self, root: str | Path | None = None) -> str:
        state = self.snapshot(root)
        visible = ", ".join(state["top_level"][:8])
        return f"Workspace {state['project']['name']} contains: {visible}"


workspace_state = WorkspaceState()
