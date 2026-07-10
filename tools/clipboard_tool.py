"""Clipboard helpers using tkinter from the Python standard library."""

from __future__ import annotations

def _with_clipboard(action):
    import tkinter
    root = tkinter.Tk()
    root.withdraw()
    try:
        return action(root)
    finally:
        root.destroy()


def read_clipboard() -> dict:
    try:
        import tkinter
        try:
            text = _with_clipboard(lambda root: root.clipboard_get())
            return {"success": True, "text": text}
        except tkinter.TclError as exc:
            return {"success": False, "error": str(exc)}
    except ImportError as e:
        return {"success": False, "error": f"Tkinter không khả dụng: {e}"}


def write_clipboard(text: str) -> dict:
    try:
        import tkinter
        try:
            def action(root):
                root.clipboard_clear()
                root.clipboard_append(text)
                root.update()

            _with_clipboard(action)
            return {"success": True}
        except tkinter.TclError as exc:
            return {"success": False, "error": str(exc)}
    except ImportError as e:
        return {"success": False, "error": f"Tkinter không khả dụng: {e}"}
