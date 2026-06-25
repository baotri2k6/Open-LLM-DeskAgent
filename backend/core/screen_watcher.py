import threading
import time
import difflib
from core.config import config
from tools.screen_reader import ocr_screenshot
from core.logger import get_logger

logger = get_logger("ai-companion.screen-watcher")

class ScreenWatcher:
    def __init__(self, change_threshold=0.15):
        self._last_text = ""
        self._current_activity = "unknown"
        self._threshold = change_threshold
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    def start(self):
        """Chạy background thread, cập nhật _last_text mỗi 5 giây."""
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
        """Nhận diện activity từ OCR text."""
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
            # Check if screenAwareness is enabled in config
            if config.get("features.screenAwareness", False):
                try:
                    res = ocr_screenshot()
                    if res.get("success"):
                        text = res.get("text", "").strip()
                        if text:
                            # Compare with last text to see if it changed significantly
                            changed = False
                            with self._lock:
                                if not self._last_text:
                                    changed = True
                                else:
                                    # Use difflib to compare similarity
                                    seq = difflib.SequenceMatcher(None, self._last_text, text)
                                    similarity = seq.ratio()
                                    if similarity < (1.0 - self._threshold):
                                        changed = True
                                
                                if changed:
                                    self._last_text = text
                                    self._current_activity = self.detect_activity(text)
                                    logger.info(f"ScreenWatcher: Screen text changed. New activity: {self._current_activity}")
                except Exception as e:
                    logger.error(f"Error in ScreenWatcher loop: {e}")
            time.sleep(5)

    def get_current_context(self) -> str:
        """Trả về OCR text hiện tại để inject vào ContextPacket."""
        with self._lock:
            return self._last_text

    def get_current_activity(self) -> str:
        """Trả về hoạt động hiện tại được phát hiện."""
        with self._lock:
            return self._current_activity

    def has_changed_significantly(self, new_text: str) -> bool:
        """True nếu màn hình thay đổi đủ nhiều so với get_current_context() để đáng comment."""
        with self._lock:
            if not self._last_text:
                return True
            seq = difflib.SequenceMatcher(None, self._last_text, new_text)
            return seq.ratio() < (1.0 - self._threshold)
