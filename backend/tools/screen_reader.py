"""Screen reader — chụp màn hình và OCR."""

from __future__ import annotations

import base64
import io
import os


def capture_screenshot() -> dict:
    """Chụp màn hình, trả về bytes PNG và base64."""
    try:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # màn hình chính
            img = sct.grab(monitor)
            # convert sang PNG bytes
            from PIL import Image
            pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            png_bytes = buf.getvalue()
        b64 = base64.b64encode(png_bytes).decode()
        return {"success": True, "png_base64": b64, "size": img.size}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def ocr_screenshot() -> dict:
    """Chụp màn hình rồi OCR bằng pytesseract."""
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