"""Detects and stores current project context."""

from __future__ import annotations

from pathlib import Path

from config.config import PROJECT_ROOT


class ProjectContext:
    """Lightweight project detector based on common manifest files."""

    MARKERS = {
        "package.json": "node",
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "composer.json": "php",
    }

    def detect(self, start_path: str | Path | None = None) -> dict:
        path = Path(start_path or PROJECT_ROOT).resolve()
        if path.is_file():
            path = path.parent

        current = path
        while True:
            markers = [name for name in self.MARKERS if (current / name).exists()]
            if markers:
                languages = sorted({self.MARKERS[name] for name in markers})
                return {
                    "root": str(current),
                    "name": current.name,
                    "markers": markers,
                    "languages": languages,
                }
            if current.parent == current:
                break
            current = current.parent

        return {"root": str(path), "name": path.name, "markers": [], "languages": []}

    def describe(self, start_path: str | Path | None = None) -> str:
        ctx = self.detect(start_path)
        langs = ", ".join(ctx["languages"]) if ctx["languages"] else "unknown stack"
        return f"Project {ctx['name']} at {ctx['root']} ({langs})"


project_context = ProjectContext()
