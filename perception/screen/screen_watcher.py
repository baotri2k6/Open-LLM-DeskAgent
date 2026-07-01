import base64
import difflib
import io
import threading
import time

from PIL import Image

from config.config import config
from runtime.logger import get_logger
from tools.screen_reader import capture_screenshot, ocr_screenshot

logger = get_logger("ai-companion.screen-watcher")


class ScreenWatcher:
    def __init__(self, change_threshold=0.15):
        self._last_text = ""
        self._current_activity = "unknown"
        self._threshold = change_threshold
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    def capture_desktop_session(self) -> Image.Image | None:
        """Capture the current desktop through the shared screen reader path."""
        shot = capture_screenshot()
        if not shot.get("success"):
            logger.warning("ScreenWatcher capture failed: %s", shot.get("error", "unknown error"))
            return None

        png_bytes = base64.b64decode(shot["png_base64"])
        return Image.open(io.BytesIO(png_bytes))

    def start(self):
        """Run the background OCR thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("ScreenWatcher thread started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        logger.info("ScreenWatcher thread stopped.")

    def detect_activity(self, ocr_text: str) -> str:
        """Infer high-level user activity from OCR text."""
        text_lower = ocr_text.lower()
        if any(k in text_lower for k in ["def ", "import ", "class ", "function", "error:", "traceback"]):
            return "coding"
        if any(k in text_lower for k in ["youtube", "netflix", "bilibili", "video"]):
            return "watching_video"
        if any(k in text_lower for k in ["steam", "game", "score", "level", "hp", "mana"]):
            return "gaming"
        if any(k in text_lower for k in ["docs.google", "word", "powerpoint", ".docx"]):
            return "working_document"
        return "unknown"

    def _run_loop(self):
        while self._running:
            if config.get("features.screenAwareness", False):
                try:
                    res = ocr_screenshot()
                    if res.get("success"):
                        text = res.get("text", "").strip()
                        if text:
                            self._update_text(text)
                except Exception as e:
                    logger.error("Error in ScreenWatcher loop: %s", e)
            time.sleep(5)

    def _update_text(self, text: str) -> None:
        with self._lock:
            if not self._last_text:
                changed = True
            else:
                similarity = difflib.SequenceMatcher(None, self._last_text, text).ratio()
                changed = similarity < (1.0 - self._threshold)

            if changed:
                self._last_text = text
                self._current_activity = self.detect_activity(text)
                logger.info("ScreenWatcher: Screen text changed. New activity: %s", self._current_activity)

    def get_current_context(self) -> str:
        """Return current OCR text for ContextPacket injection."""
        with self._lock:
            return self._last_text

    def get_current_activity(self) -> str:
        """Return the current detected activity."""
        with self._lock:
            return self._current_activity

    def has_changed_significantly(self, new_text: str) -> bool:
        """Return True when new OCR text differs enough from current context."""
        with self._lock:
            if not self._last_text:
                return True
            similarity = difflib.SequenceMatcher(None, self._last_text, new_text).ratio()
            return similarity < (1.0 - self._threshold)
