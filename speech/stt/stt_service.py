"""Speech-to-Text service — Whisper local.

Thứ tự ưu tiên:
1. faster-whisper (nhanh hơn ~4×, ít RAM)
2. openai-whisper (fallback)
3. Lỗi có hướng dẫn cài đặt rõ ràng
"""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Literal

from config.config import config
from runtime.logger import get_logger

logger = get_logger("ai-companion.stt")

WhisperModel = Literal["tiny", "base", "small", "medium", "large"]

import asyncio

class STTService:
    def __init__(self):
        self.model = None
        self.status = "offline" # Trạng thái ban đầu

    async def initialize_model_async(self):
        """Hàm nạp model chạy ngầm không chặn luồng khởi động FastAPI"""
        self.status = "loading"
        try:
            # Giả lập nạp mô hình FunASR / SenseVoiceSmall cục bộ
            # self.model = AutoModel(model="iic/SenseVoiceSmall", ...)
            await asyncio.sleep(2) # Giả lập thời gian load weights vào RAM
            self.status = "ready"
        except Exception:
            self.status = "error"
# ─── faster-whisper api ──────────────────────────────────────────────────

class _FasterWhisperSTT:
    def __init__(self, model_size: str = "base") -> None:
        from faster_whisper import WhisperModel as FW
        device = "cpu"
        compute = "int8"
        logger.info("Loading faster-whisper '%s' on %s/%s", model_size, device, compute)
        self._model = FW(model_size, device=device, compute_type=compute)
        logger.info("faster-whisper ready")

    def transcribe(self, audio_path: str, language: str = "vi") -> str:
        lang = None if language in ("auto", None) else language
        segments, info = self._model.transcribe(audio_path, language=lang, beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        logger.info("Transcribed %d chars (detected_lang=%s, prob=%.2f)", len(text), info.language, info.language_probability)
        return text


# ─── openai-whisper api ──────────────────────────────────────────────────

class _OpenAIWhisperSTT:
    def __init__(self, model_size: str = "base") -> None:
        import whisper
        logger.info("Loading openai-whisper '%s'", model_size)
        self._model = whisper.load_model(model_size)
        logger.info("openai-whisper ready")

    def transcribe(self, audio_path: str, language: str = "vi") -> str:
        lang = None if language in ("auto", None) else language
        result = self._model.transcribe(audio_path, language=lang, fp16=False)
        return result["text"].strip()


class _FunASRSTT:
    def __init__(self, model_name: str = "iic/SenseVoiceSmall") -> None:
        from funasr import AutoModel
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading FunASR model '%s' on %s", model_name, device)
        self._model = AutoModel(
            model=model_name,
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            device=device,
            disable_update=True
        )
        logger.info("FunASR ready")

    def transcribe(self, audio_path: str, language: str = "vi") -> str:
        try:
            res = self._model.generate(input=audio_path, cache={}, language=language)
        except Exception:
            res = self._model.generate(input=audio_path)
            
        if res and isinstance(res, list) and len(res) > 0:
            return res[0].get("text", "").strip()
        return ""


# ─── STTService facade ───────────────────────────────────────────────────────

class STTService:
    def __init__(self) -> None:
        model_size: str = config.get("stt.model", "base")
        language: str = config.get("stt.language", "vi")
        self._language = language
        self._backend = self._load_backend(model_size)
        self._lock = threading.Lock()

    def _load_backend(self, model_size: str):
        if model_size == "funasr":
            funasr_model = config.get("stt.funasr_model", "iic/SenseVoiceSmall")
            try:
                return _FunASRSTT(funasr_model)
            except Exception as e:
                logger.error(
                    "Không nạp được FunASR api: %s. "
                    "Hãy chắc chắn đã chạy: pip install funasr modelscope torchaudio. "
                    "Fallback về Whisper base...", e
                )
                model_size = "base"

        try:
            return _FasterWhisperSTT(model_size)
        except ImportError:
            logger.warning("faster-whisper not found, trying openai-whisper")
        try:
            return _OpenAIWhisperSTT(model_size)
        except ImportError:
            logger.error(
                "Không tìm thấy Whisper api. "
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
            with self._lock:
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