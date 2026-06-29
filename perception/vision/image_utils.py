"""Image processing utilities for vision models."""

from __future__ import annotations

import base64
import io


def resize_image_bytes(image_bytes: bytes, max_size: tuple[int, int] = (800, 800)) -> bytes:
    """Resize image to prevent large payload sizes when sending to VLMs."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail(max_size)
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return image_bytes


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Convert raw image bytes to base64 string representation."""
    return base64.b64encode(image_bytes).decode("utf-8")
