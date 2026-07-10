"""Line-numbered source file viewer for coding agents."""

from __future__ import annotations

from pathlib import Path


def view_file(path: str, start_line: int = 1, end_line: int | None = None) -> dict:
    """Return a line-numbered view of a text file."""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return {"success": False, "error": f"File does not exist: {path}"}
        if not p.is_file():
            return {"success": False, "error": f"Path is not a file: {path}"}

        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        total_lines = len(lines)
        start = max(int(start_line or 1), 1)
        end = int(end_line) if end_line is not None else total_lines
        end = min(max(end, start), total_lines)

        selected = lines[start - 1:end]
        numbered = "\n".join(
            f"{line_no:>5} | {line}"
            for line_no, line in enumerate(selected, start=start)
        )
        return {
            "success": True,
            "path": str(p),
            "start_line": start,
            "end_line": end,
            "total_lines": total_lines,
            "text": numbered,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
