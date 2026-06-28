"""GroundingEngine — Maps natural language query to screen coordinates using OCR."""

from __future__ import annotations

import io
import base64
import logging
from typing import Tuple, Optional
import difflib

from tools.screen_reader import capture_screenshot

logger = logging.getLogger("ai-companion.vision.grounding")


class GroundingEngine:
    """Maps natural language queries (like button/text names) to screen coordinates."""

    def __init__(self) -> None:
        pass

    def ground(self, element_desc: str) -> Optional[Tuple[int, int]]:
        """Find the coordinates of a visual element matching the description.

        Args:
            element_desc: Natural language query (e.g., "Sign In").

        Returns:
            Tuple (x, y) coordinates of the element on the screen, or None if not found.
        """
        logger.info("Grounding element description: '%s'", element_desc)
        
        # 1. Capture screen
        shot = capture_screenshot()
        if not shot.get("success"):
            logger.warning("Screen capture failed for grounding")
            return None

        # 2. Get OCR details with coordinates via pytesseract
        try:
            import pytesseract
            from PIL import Image
            
            png_bytes = base64.b64decode(shot["png_base64"])
            img = Image.open(io.BytesIO(png_bytes))
            
            # Get word boxes: tesseract returns dict with left, top, width, height, text
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang="vie+eng")
            
            # Try to match the query element_desc
            query = element_desc.lower().strip()
            
            # Standard single word or adjacent words matching
            n_items = len(data["text"])
            
            # Simple matching: search for exact or fuzzy substring in OCR texts
            for i in range(n_items):
                word = str(data["text"][i]).strip()
                if not word:
                    continue
                
                # Check match
                if query in word.lower() or word.lower() in query:
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    logger.info("Found exact/fuzzy grounding match for '%s' at (%d, %d)", element_desc, x, y)
                    return x, y
                    
            # Phrase matching: try combining adjacent words
            for i in range(n_items - 1):
                word1 = str(data["text"][i]).strip()
                word2 = str(data["text"][i+1]).strip()
                combined = f"{word1} {word2}".lower()
                if query in combined or combined in query:
                    # average position
                    x = (data["left"][i] + data["left"][i+1] + data["width"][i] + data["width"][i+1]) // 2
                    y = (data["top"][i] + data["top"][i+1] + data["height"][i] + data["height"][i+1]) // 2
                    logger.info("Found multi-word grounding match for '%s' at (%d, %d)", element_desc, x, y)
                    return x, y

            logger.warning("Element '%s' not found on screen", element_desc)
            return None

        except Exception as e:
            logger.error("Error running pytesseract data search: %s", e)
            return None


# Global singleton
grounding_engine = GroundingEngine()
