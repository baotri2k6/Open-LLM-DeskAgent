"""Detects UI elements and objects on screen."""

from __future__ import annotations

import base64
import io

from tools.screen_reader import capture_screenshot


class ObjectDetector:
    """OCR-backed UI element detector.

    This is intentionally lightweight: it extracts visible text boxes when
    pytesseract is available and returns an empty list otherwise.
    """

    def detect_text_elements(self) -> list[dict]:
        shot = capture_screenshot()
        if not shot.get("success"):
            return []

        try:
            import pytesseract
            from PIL import Image

            image = Image.open(io.BytesIO(base64.b64decode(shot["png_base64"])))
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, lang="vie+eng")
        except Exception:
            return []

        elements: list[dict] = []
        for idx, text in enumerate(data.get("text", [])):
            label = str(text).strip()
            if not label:
                continue
            elements.append({
                "type": "text",
                "text": label,
                "bbox": {
                    "x": int(data["left"][idx]),
                    "y": int(data["top"][idx]),
                    "width": int(data["width"][idx]),
                    "height": int(data["height"][idx]),
                },
                "confidence": float(data.get("conf", [0])[idx] or 0),
            })
        return elements

    def detect(self) -> dict:
        elements = self.detect_text_elements()
        return {"success": True, "elements": elements, "count": len(elements)}


object_detector = ObjectDetector()
