"""Parses screen content into structured data."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.vision.parser")


class ScreenParser:
    """Parses screen content into structured data."""

    def __init__(self) -> None:
        pass

    def parse_screen_text(self, raw_text: str) -> list[str]:
        """Split and extract non-empty lines from OCR text."""
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        return lines


# Global singleton
screen_parser = ScreenParser()
