"""Text-to-Speech service.

Thứ tự ưu tiên backend:
1. fish_audio  — voice cloning API, giọng anime/VTuber cực tự nhiên
2. edge-tts    — Microsoft Edge Neural TTS (miễn phí, cần internet)
3. pyttsx3     — offline, cần Windows SAPI / eSpeak
4. Stub        — trả về text, không có audio
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import struct
import urllib.request
import urllib.error
from pathlib import Path

from core.config import PROJECT_ROOT, config
from core.logger import get_logger

logger = get_logger("ai-companion.tts")

TTS_CACHE = PROJECT_ROOT / "cache" / "tts"
TTS_CACHE.mkdir(parents=True, exist_ok=True)


def _cache_path(text: str, voice_key: str, ext: str = ".mp3") -> Path:
    key = hashlib.md5(f"{voice_key}::{text}".encode()).hexdigest()
    return TTS_CACHE / f"{key}{ext}"


def _get_active_persona_tts_config() -> dict:
    try:
        from core.config import config
        avatar_model = config.get("app.avatarModel", "IceGirl")
        persona_name = "icegirl"
        avatar_model_lower = avatar_model.lower()
        if "hiyori" in avatar_model_lower:
            persona_name = "hiyori"
        elif "mao" in avatar_model_lower:
            persona_name = "mao"
        elif "huohuo" in avatar_model_lower:
            persona_name = "huohuo"
            
        from persona.persona_manager import PersonaManager
        persona_mgr = PersonaManager()
        persona = persona_mgr.load_persona(persona_name)
        if isinstance(persona, dict):
            return persona.get("tts", {})
    except Exception as exc:
        logger.warning("Failed to load persona for TTS: %s", exc)
    return {}


# ─── Fish Audio backend ───────────────────────────────────────────────────────

class _FishAudioTTS:
    """
    Fish Audio TTS API — voice cloning, giọng anime/VTuber tự nhiên.
    Tài liệu: https://docs.fish.audio
    Đăng ký miễn phí tại fish.audio → API Keys → tạo key mới.
    """

    API_URL = "https://api.fish.audio/v1/tts"

    def __init__(self) -> None:
        self._api_key    = config.get("tts.fish_audio_api_key", "")
        self._chunk_size = 4096

        if not self._api_key:
            raise ValueError("fish_audio_api_key chưa được cấu hình trong companion.config.json")
        logger.info("Fish Audio TTS backend initialized")

    async def synthesize(self, text: str) -> dict:
        tts_cfg = _get_active_persona_tts_config()
        model_id = tts_cfg.get("fish_audio_model_id") or config.get("tts.fish_audio_model_id", "")
        if not model_id:
            return {"success": False, "error": "fish_audio_model_id chưa được cấu hình."}

        out_path = _cache_path(text, f"fish:{model_id}", ext=".mp3")
        if out_path.exists():
            return {"success": True, "audio_path": str(out_path), "cached": True}

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._call_api, text, out_path, model_id)

        if out_path.exists() and out_path.stat().st_size > 0:
            logger.info("Fish Audio synthesized → %s", out_path.name)
            return {"success": True, "audio_path": str(out_path), "cached": False}

        return {"success": False, "error": "Fish Audio không trả về audio."}

    def _call_api(self, text: str, out_path: Path, model_id: str) -> None:
        """Gọi Fish Audio API (sync, chạy trong executor)."""
        payload = json.dumps({
            "text":           text,
            "reference_id":   model_id,
            "format":         "mp3",
            "mp3_bitrate":    128,
            "normalize":      True,
            "latency":        "normal",
        }).encode()

        req = urllib.request.Request(
            self.API_URL,
            data    = payload,
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type":  "application/json",
                "Accept":        "audio/mpeg",
            },
            method = "POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(out_path, "wb") as f:
                while chunk := resp.read(self._chunk_size):
                    f.write(chunk)


# ─── edge-tts backend ────────────────────────────────────────────────────────

class _EdgeTTS:
    """Microsoft Edge Neural TTS."""

    DEFAULT_VOICE = "vi-VN-HoaiMyNeural"

    def __init__(self, voice: str | None = None) -> None:
        import edge_tts  # noqa: F401
        logger.info("edge-tts backend initialized")

    async def synthesize(self, text: str) -> dict:
        import edge_tts
        tts_cfg = _get_active_persona_tts_config()
        voice = tts_cfg.get("voice") or config.get("tts.voice", self.DEFAULT_VOICE)
        pitch = tts_cfg.get("pitch") or config.get("tts.pitch", "+20%")
        
        rate_cfg = tts_cfg.get("rate") or config.get("tts.rate")
        if isinstance(rate_cfg, str) and rate_cfg.endswith("%"):
            rate = rate_cfg
        else:
            rate = "+10%"

        out_path = _cache_path(text, f"{voice}:{pitch}:{rate}", ext=".mp3")
        if out_path.exists():
            return {"success": True, "audio_path": str(out_path), "cached": True}

        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=rate,
            pitch=pitch,
        )
        await communicate.save(str(out_path))
        logger.info("edge-tts synthesized → %s (voice=%s, pitch=%s, rate=%s)", out_path.name, voice, pitch, rate)
        return {"success": True, "audio_path": str(out_path), "cached": False}


# ─── pyttsx3 backend ─────────────────────────────────────────────────────────

class _Pyttsx3TTS:
    def __init__(self) -> None:
        import pyttsx3
        self._engine = pyttsx3.init()
        logger.info("pyttsx3 backend initialized")

    async def synthesize(self, text: str) -> dict:
        tts_cfg = _get_active_persona_tts_config()
        voice = tts_cfg.get("voice") or config.get("tts.voice", "")
        rate_cfg = tts_cfg.get("rate") or config.get("tts.rate", 160)
        
        try:
            rate = int(rate_cfg)
        except (ValueError, TypeError):
            rate = 160

        out_path = _cache_path(text, f"pyttsx3:{voice}:{rate}", ext=".wav")
        if out_path.exists():
            return {"success": True, "audio_path": str(out_path), "cached": True}

        def _speak_sync():
            if voice:
                self._engine.setProperty("voice", voice)
            self._engine.setProperty("rate", rate)
            self._engine.save_to_file(text, str(out_path))
            self._engine.runAndWait()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _speak_sync)
        if out_path.exists() and out_path.stat().st_size > 0:
            return {"success": True, "audio_path": str(out_path), "cached": False}
        return {"success": False, "error": "pyttsx3 không tạo được file audio."}


# ─── GPT-SoVITS backend ───────────────────────────────────────────────────────

class _GPTSoVITSTTS:
    """
    GPT-SoVITS local TTS backend.
    Yêu cầu chạy server API GPT-SoVITS local trước.
    URL mặc định: http://127.0.0.1:9880/tts
    """

    def __init__(self) -> None:
        self._chunk_size = 4096
        logger.info("GPT-SoVITS TTS backend initialized")

    async def synthesize(self, text: str) -> dict:
        tts_cfg = _get_active_persona_tts_config()
        
        api_url = tts_cfg.get("gpt_sovits_api_url") or config.get("tts.gpt_sovits_api_url", "http://127.0.0.1:9880/tts")
        text_lang = tts_cfg.get("gpt_sovits_text_lang") or config.get("tts.gpt_sovits_text_lang", "vi")
        ref_audio_path = tts_cfg.get("gpt_sovits_ref_audio_path") or config.get("tts.gpt_sovits_ref_audio_path", "")
        prompt_lang = tts_cfg.get("gpt_sovits_prompt_lang") or config.get("tts.gpt_sovits_prompt_lang", "vi")
        prompt_text = tts_cfg.get("gpt_sovits_prompt_text") or config.get("tts.gpt_sovits_prompt_text", "")

        out_path = _cache_path(
            text,
            f"gpt_sovits:{text_lang}:{ref_audio_path}:{prompt_text}",
            ext=".wav"
        )
        if out_path.exists():
            return {"success": True, "audio_path": str(out_path), "cached": True}

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._call_api,
            text,
            out_path,
            api_url,
            text_lang,
            ref_audio_path,
            prompt_lang,
            prompt_text
        )

        if out_path.exists() and out_path.stat().st_size > 0:
            logger.info("GPT-SoVITS synthesized → %s", out_path.name)
            return {"success": True, "audio_path": str(out_path), "cached": False}

        return {"success": False, "error": "GPT-SoVITS không trả về audio."}

    def _call_api(self, text: str, out_path: Path, api_url: str, text_lang: str, ref_audio_path: str, prompt_lang: str, prompt_text: str) -> None:
        import urllib.parse
        
        params = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_lang": prompt_lang,
            "prompt_text": prompt_text,
            "text_split_method": "cut5",
            "batch_size": 1,
            "media_type": "wav",
            "streaming_mode": "false",
        }
        
        params = {k: v for k, v in params.items() if v is not None and v != ""}
        query_string = urllib.parse.urlencode(params)
        full_url = f"{api_url}?{query_string}"
        
        req = urllib.request.Request(full_url, method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(out_path, "wb") as f:
                while chunk := resp.read(self._chunk_size):
                    f.write(chunk)



# ─── TTSService facade ────────────────────────────────────────────────────────

class TTSService:
    def __init__(self) -> None:
        self._backend = self._load_backend()
        self._edge_backend = None
        self._pyttsx3_backend = None
        self._clean_old_cache()

    def _clean_old_cache(self, max_files: int = 100) -> None:
        try:
            files = list(TTS_CACHE.glob("*.mp3")) + list(TTS_CACHE.glob("*.wav"))
            if len(files) <= max_files:
                return
            # Sắp xếp theo thời gian sửa đổi (mtime) giảm dần (mới nhất lên đầu)
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            # Xóa các file cũ vượt quá số lượng tối đa
            for f in files[max_files:]:
                try:
                    f.unlink()
                except Exception:
                    pass
            logger.info("Cleaned TTS cache: kept %d most recent files", max_files)
        except Exception as exc:
            logger.warning("Failed to clean TTS cache: %s", exc)

    def _load_backend(self):
        preferred = config.get("tts.backend", "edge")

        if preferred == "gpt_sovits":
            try:
                return _GPTSoVITSTTS()
            except Exception as exc:
                logger.warning("GPT-SoVITS init failed: %s", exc)

        if preferred == "fish_audio":
            try:
                return _FishAudioTTS()
            except Exception as exc:
                logger.warning("Fish Audio init failed: %s", exc)

        if preferred in ("edge", "auto"):
            try:
                return _EdgeTTS()
            except ImportError:
                logger.warning("edge-tts not found. pip install edge-tts")

        if preferred in ("pyttsx3", "auto"):
            try:
                return _Pyttsx3TTS()
            except Exception as exc:
                logger.warning("pyttsx3 failed: %s", exc)

        logger.warning("TTS chạy ở chế độ stub (không có audio).")
        return None

    @property
    def available(self) -> bool:
        return self._backend is not None

    async def speak(self, text: str) -> dict:
        text = text.strip()
        if not text:
            return {"success": False, "error": "Text rỗng."}

        backends_to_try = []
        if self._backend:
            backends_to_try.append(self._backend)

        # Fallback 1: EdgeTTS
        if not isinstance(self._backend, _EdgeTTS):
            if not self._edge_backend:
                try:
                    self._edge_backend = _EdgeTTS()
                except Exception:
                    pass
            if self._edge_backend:
                backends_to_try.append(self._edge_backend)

        # Fallback 2: Pyttsx3
        if not isinstance(self._backend, _Pyttsx3TTS):
            if not self._pyttsx3_backend:
                try:
                    self._pyttsx3_backend = _Pyttsx3TTS()
                except Exception:
                    pass
            if self._pyttsx3_backend:
                backends_to_try.append(self._pyttsx3_backend)

        for backend in backends_to_try:
            try:
                result = await backend.synthesize(text)
                if result.get("success"):
                    audio_path = result["audio_path"]
                    est_ms = max(800, int(len(text) / 150 * 1000))
                    return {
                        "success":    True,
                        "text":       text,
                        "audio_path": audio_path,
                        "audio_url":  f"/tts/cache/{Path(audio_path).name}",
                        "duration_ms": est_ms,
                        "cached":     result.get("cached", False),
                    }
                else:
                    logger.warning("TTS backend %s failed: %s", backend.__class__.__name__, result.get("error"))
            except Exception as exc:
                logger.warning("TTS backend %s raised exception: %s", backend.__class__.__name__, exc)

        # Fallback cuối cùng: Stub mode (chỉ hiện chữ, không tiếng)
        return {
            "success":    True,
            "text":       text,
            "audio_path": None,
            "audio_url":  None,
            "duration_ms": 0,
            "stub":       True,
        }