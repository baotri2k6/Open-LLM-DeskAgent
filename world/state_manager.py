"""Aggregates all world sub-states into one snapshot."""

from __future__ import annotations

from datetime import datetime

from world.activity.activity_tracker import activity_tracker
from world.applications.app_tracker import app_tracker
from world.desktop.desktop_state import desktop_state
from world.projects.project_context import project_context
from world.windows.window_tracker import window_tracker
from world.workspace.workspace_state import workspace_state


class WorldStateManager:
    """Builds a single world snapshot for agents and prompts."""

    def snapshot(self) -> dict:
        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "activity": activity_tracker.get_current_activity(),
            "active_window": window_tracker.get_active_window(),
            "running_apps": app_tracker.get_running_apps(),
            "desktop": desktop_state.snapshot(),
            "project": project_context.detect(),
            "workspace": workspace_state.snapshot(),
        }

    def describe(self) -> str:
        snap = self.snapshot()
        activity = snap["activity"]
        return f"{activity.get('details', 'Unknown activity')} | Project: {snap['project'].get('name')}"


world_state_manager = WorldStateManager()
