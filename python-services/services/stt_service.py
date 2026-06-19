"""Speech-to-Text service — Whisper local.

Thứ tự ưu tiên:
1. faster-whisper (nhanh hơn ~4×, ít RAM)
2. openai-whisper (fallback)
3. Lỗi có hướng dẫn cài đặt rõ ràng
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Literal

from core.config import config
from core.logger import get_logger

logger = get_logger("ai-companion.stt")

WhisperModel = Literal["tiny", "base", "small", "medium", "large"]


# ─── faster-whisper backend ──────────────────────────────────────────────────

class _FasterWhisperSTT:
    def __init__(self, model_size: str = "base") -> None:
        from faster_whisper import WhisperModel as FW
        device = "cpu"
        compute = "int8"
        logger.info("Loading faster-whisper '%s' on %s/%s", model_size, device, compute)
        self._model = FW(model_size, device=device, compute_type=compute)
        logger.info("faster-whisper ready")

    def transcribe(self, audio_path: str, language: str = "vi") -> str:
        segments, info = self._model.transcribe(audio_path, language=language, beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        logger.info("Transcribed %d chars (lang=%s, prob=%.2f)", len(text), info.language, info.language_probability)
        return text


# ─── openai-whisper backend ──────────────────────────────────────────────────

class _OpenAIWhisperSTT:
    def __init__(self, model_size: str = "base") -> None:
        import whisper
        logger.info("Loading openai-whisper '%s'", model_size)
        self._model = whisper.load_model(model_size)
        logger.info("openai-whisper ready")

    def transcribe(self, audio_path: str, language: str = "vi") -> str:
        result = self._model.transcribe(audio_path, language=language, fp16=False)
        return result["text"].strip()


# ─── STTService facade ───────────────────────────────────────────────────────

class STTService:
    def __init__(self) -> None:
        model_size: str = config.get("stt.model", "base")
        language: str = config.get("stt.language", "vi")
        self._language = language
        self._backend = self._load_backend(model_size)

    def _load_backend(self, model_size: str):
        try:
            return _FasterWhisperSTT(model_size)
        except ImportError:
            logger.warning("faster-whisper not found, trying openai-whisper")
        try:
            return _OpenAIWhisperSTT(model_size)
        except ImportError:
            logger.error(
                "Không tìm thấy Whisper backend. "
                "Cài đặt: pip install faster-whisper  hoặc  pip install openai-whisper"
            )
            return None

    @property
    def available(self) -> bool:
        return self._backend is not None

    async def transcribe(self, audio_path: str, language: str | None = None) -> dict:
        """
        Nhận path file âm thanh (WAV/MP3/WebM), trả về:
        {success, text, language}
        """
        if not self._backend:
            return {
                "success": False,
                "error": (
                    "STT chưa sẵn sàng. Cài đặt: "
                    "pip install faster-whisper"
                ),
            }
        lang = language or self._language
        try:
            text = self._backend.transcribe(audio_path, language=lang)
            return {"success": True, "text": text, "language": lang}
        except Exception as exc:
            logger.error("STT error: %s", exc)
            return {"success": False, "error": str(exc)}

    async def transcribe_bytes(self, audio_bytes: bytes, suffix: str = ".wav") -> dict:
        """Nhận raw bytes, lưu vào temp file rồi transcribe."""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            return await self.transcribe(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass