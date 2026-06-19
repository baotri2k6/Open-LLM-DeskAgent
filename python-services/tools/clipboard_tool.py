"""Clipboard helpers using tkinter from the Python standard library."""

from __future__ import annotations

import tkinter


def _with_clipboard(action):
    root = tkinter.Tk()
    root.withdraw()
    try:
        return action(root)
    finally:
        root.destroy()


def read_clipboard() -> dict:
    try:
        text = _with_clipboard(lambda root: root.clipboard_get())
        return {"success": True, "text": text}
    except tkinter.TclError as exc:
        return {"success": False, "error": str(exc)}


def write_clipboard(text: str) -> dict:
    try:
        def action(root):
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()

        _with_clipboard(action)
        return {"success": True}
    except tkinter.TclError as exc:
        return {"success": False, "error": str(exc)}
