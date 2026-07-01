"""Screen reader utilities for screenshot capture and OCR."""

from __future__ import annotations

import base64
import io


def _encode_png(pil_img) -> dict:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    return {
        "success": True,
        "png_base64": base64.b64encode(png_bytes).decode(),
        "size": pil_img.size,
    }


def capture_screenshot() -> dict:
    """Capture the primary screen as PNG bytes encoded in base64."""
    try:
        import mss
        from PIL import Image

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
        return _encode_png(pil_img)
    except Exception as mss_exc:
        try:
            import pyautogui

            return _encode_png(pyautogui.screenshot())
        except Exception as pyautogui_exc:
            return {
                "success": False,
                "error": f"mss failed: {mss_exc}; pyautogui failed: {pyautogui_exc}",
            }


def ocr_screenshot() -> dict:
    """Capture the screen and extract visible text with pytesseract."""
    shot = capture_screenshot()
    if not shot.get("success"):
        return shot
    try:
        import pytesseract
        from PIL import Image

        png_bytes = base64.b64decode(shot["png_base64"])
        img = Image.open(io.BytesIO(png_bytes))
        text = pytesseract.image_to_string(img, lang="vie+eng")
        return {"success": True, "text": text.strip(), "size": shot["size"]}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
