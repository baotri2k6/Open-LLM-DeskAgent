"""Text-to-Speech service.

Thứ tự ưu tiên api:
1. fish_audio  — voice cloning API, giọng anime/VTuber cực tự nhiên
2. edge-tts    — Microsoft Edge Neural TTS (miễn phí, cần internet)
3. pyttsx3     — offline, cần Windows SAPI / eSpeak
4. Stub        — trả về text, không có audio
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import struct
import urllib.request
import urllib.error
from pathlib import Path

from config.config import WRITABLE_ROOT, config
from runtime.logger import get_logger

logger = get_logger("ai-companion.tts")

TTS_CACHE = WRITABLE_ROOT / "cache" / "tts"
TTS_CACHE.mkdir(parents=True, exist_ok=True)


def _cache_path(text: str, voice_key: str, ext: str = ".mp3") -> Path:
    key = hashlib.md5(f"{voice_key}::{text}".encode()).hexdigest()
    return TTS_CACHE / f"{key}{ext}"


def _get_active_persona_tts_config() -> dict:
    try:
        from config.config import config
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


def is_vietnamese(text: str) -> bool:
    """Định dạng nhanh để kiểm tra xem văn bản là Tiếng Việt hay Tiếng Anh."""
    vi_chars = set("áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ"
                   "ÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ")
    if any(c in vi_chars for c in text):
        return True
        
    vi_words = {
        "và", "của", "cho", "như", "được", "trong", "có", "một", "không", "tôi", 
        "bạn", "cậu", "tớ", "này", "đó", "nè", "nha", "đang", "là", "với", "hơn", 
        "lại", "nếu", "thế", "cái", "con", "gì", "nào", "ở", "về", "đã", "mới",
        "chào", "khoe", "học", "làm", "chơi"
    }
    words = [w.strip(",.!?()\"'").lower() for w in text.split()]
    if any(w in vi_words for w in words):
        return True
        
    return False


# ─── Fish Audio api ───────────────────────────────────────────────────────

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
        logger.info("Fish Audio TTS api initialized")

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


# ─── edge-tts api ────────────────────────────────────────────────────────

class _EdgeTTS:
    """Microsoft Edge Neural TTS."""

    DEFAULT_VOICE = "vi-VN-HoaiMyNeural"

    def __init__(self, voice: str | None = None) -> None:
        import edge_tts  # noqa: F401
        logger.info("edge-tts api initialized")

    async def synthesize(self, text: str) -> dict:
        import edge_tts
        tts_cfg = _get_active_persona_tts_config()
        voice = tts_cfg.get("voice") or config.get("tts.voice", self.DEFAULT_VOICE)
        
        # Sanitize pitch (must match r"^[+-]\d+Hz$")
        pitch_val = tts_cfg.get("pitch") or config.get("tts.pitch") or "+20Hz"
        if isinstance(pitch_val, str):
            pitch = pitch_val.replace("%", "Hz")
            if not pitch.endswith("Hz"):
                pitch = pitch + "Hz"
            if not (pitch.startswith("+") or pitch.startswith("-")):
                pitch = "+" + pitch
        else:
            pitch = "+20Hz"
            
        # Nếu là tiếng Anh mà cấu hình giọng nói lại là tiếng Việt, tự động chuyển sang giọng tiếng Anh dễ thương
        if not is_vietnamese(text) and voice.startswith("vi-"):
            voice = "en-US-EmmaNeural"
            pitch = "+10Hz"
        
        # Sanitize rate (must match r"^[+-]\d+%$")
        rate_cfg = tts_cfg.get("rate") or config.get("tts.rate")
        if isinstance(rate_cfg, str):
            rate = rate_cfg
            if not rate.endswith("%"):
                rate = rate + "%"
            if not (rate.startswith("+") or rate.startswith("-")):
                rate = "+" + rate
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


# ─── pyttsx3 api ─────────────────────────────────────────────────────────

class _Pyttsx3TTS:
    def __init__(self) -> None:
        import pyttsx3
        self._engine = pyttsx3.init()
        logger.info("pyttsx3 api initialized")

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


# ─── GPT-SoVITS api ───────────────────────────────────────────────────────

class _GPTSoVITSTTS:
    """
    GPT-SoVITS local TTS api.
    Yêu cầu chạy server API GPT-SoVITS local trước.
    URL mặc định: http://127.0.0.1:9880/tts
    """

    def __init__(self) -> None:
        self._chunk_size = 4096
        logger.info("GPT-SoVITS TTS api initialized")

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



# ─── Kokoro TTS api ───────────────────────────────────────────────────────

class _KokoroTTS:
    """
    Kokoro-82M offline TTS api.
    Yêu cầu:
    1. pip install kokoro soundfile
    2. Cài đặt espeak-ng trên hệ thống (để chuyển text thành phonemes)
    """

    def __init__(self) -> None:
        import sys
        
        # Tự động thiết lập đường dẫn espeak-ng mặc định trên Windows nếu chưa được thiết lập
        if sys.platform == "win32":
            if not os.environ.get("PHONEMIZER_ESPEAK_PATH"):
                paths_to_check = [
                    r"C:\Program Files\eSpeak NG",
                    r"C:\Program Files (x86)\eSpeak NG"
                ]
                for p in paths_to_check:
                    if os.path.exists(p):
                        os.environ["PHONEMIZER_ESPEAK_PATH"] = p
                        lib_path = os.path.join(p, "libespeak-ng.dll")
                        if os.path.exists(lib_path):
                            os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = lib_path
                        logger.info("Auto-configured espeak-ng paths: %s", p)
                        break

        try:
            from kokoro import KPipeline
        except ImportError:
            raise ImportError(
                "Không tìm thấy thư viện kokoro. Vui lòng cài đặt:\n"
                "  pip install kokoro soundfile\n"
                "Và cài đặt phần mềm espeak-ng trên hệ thống."
            )

        lang_code = config.get("tts.kokoro_lang", "a")
        logger.info("Initializing Kokoro KPipeline with lang_code '%s'", lang_code)
        
        # Khởi tạo pipeline
        try:
            self._pipeline = KPipeline(lang_code=lang_code)
        except Exception as e:
            logger.error("Failed to initialize Kokoro KPipeline: %s", e)
            raise RuntimeError(
                f"Lỗi khởi tạo Kokoro pipeline: {e}. "
                "Hãy đảm bảo bạn đã cài đặt espeak-ng và đặt đúng biến môi trường."
            )
        
        logger.info("Kokoro TTS api ready")

    async def synthesize(self, text: str) -> dict:
        import soundfile as sf
        import numpy as np

        tts_cfg = _get_active_persona_tts_config()
        voice = tts_cfg.get("kokoro_voice") or config.get("tts.kokoro_voice", "af_sarah")
        speed = float(tts_cfg.get("kokoro_speed") or config.get("tts.kokoro_speed", 1.0))

        out_path = _cache_path(text, f"kokoro:{voice}:{speed}", ext=".wav")
        if out_path.exists():
            return {"success": True, "audio_path": str(out_path), "cached": True}

        def _generate():
            generator = self._pipeline(text, voice=voice, speed=speed, split_pattern=r'\n+')
            all_audio = []
            for _, _, audio in generator:
                if audio is not None and len(audio) > 0:
                    all_audio.append(audio)
            
            if not all_audio:
                raise ValueError("Kokoro không tạo ra dữ liệu âm thanh nào.")
            
            combined = np.concatenate(all_audio)
            sf.write(str(out_path), combined, 24000)

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, _generate)
        except Exception as e:
            logger.error("Kokoro synthesis error: %s", e)
            return {"success": False, "error": str(e)}

        if out_path.exists() and out_path.stat().st_size > 0:
            logger.info("Kokoro synthesized → %s (voice=%s, speed=%s)", out_path.name, voice, speed)
            return {"success": True, "audio_path": str(out_path), "cached": False}

        return {"success": False, "error": "Kokoro không tạo được file audio."}


# ─── MOSS-TTS api ─────────────────────────────────────────────────────────

class _MossTTS:
    """
    MOSS-TTS / MOSS-TTS-Nano CPU-optimized offline/online TTS api.
    Hỗ trợ 2 chế độ:
    1. 'api' (FastAPI server POST tới /api/generate)
    2. 'cli' (chạy infer_onnx.py của MOSS-TTS-Nano thông qua subprocess)
    """

    def __init__(self) -> None:
        self._mode = config.get("tts.moss_mode", "api")
        self._api_url = config.get("tts.moss_api_url", "http://127.0.0.1:18083/api/generate")
        self._voice = config.get("tts.moss_voice", "Junhao")
        self._dir = config.get("tts.moss_dir", "")
        self._ref_audio_path = config.get("tts.moss_ref_audio_path", "")
        self._prompt_text = config.get("tts.moss_prompt_text", "")
        logger.info("MOSS-TTS initialized (mode=%s, voice=%s)", self._mode, self._voice)

    async def synthesize(self, text: str) -> dict:
        if self._mode == "cli":
            return await self._synthesize_cli(text)
        else:
            return await self._synthesize_api(text)

    async def _synthesize_api(self, text: str) -> dict:
        out_path = _cache_path(text, f"moss_api:{self._voice}", ext=".wav")
        if out_path.exists():
            return {"success": True, "audio_path": str(out_path), "cached": True}

        try:
            import urllib.request
            import urllib.error
            import uuid
            
            boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
            parts = []
            
            parts.append(f"--{boundary}")
            parts.append('Content-Disposition: form-data; name="text"')
            parts.append('')
            parts.append(text)
            
            parts.append(f"--{boundary}")
            parts.append('Content-Disposition: form-data; name="demo_id"')
            parts.append('')
            parts.append(self._voice)
            
            parts.append(f"--{boundary}--")
            parts.append('')
            
            body = "\r\n".join(parts).encode("utf-8")
            
            req = urllib.request.Request(
                self._api_url,
                data=body,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}"
                },
                method="POST"
            )
            
            loop = asyncio.get_event_loop()
            
            def _call():
                with urllib.request.urlopen(req, timeout=30) as resp:
                    with open(out_path, "wb") as f:
                        f.write(resp.read())
            
            await loop.run_in_executor(None, _call)
            
            if out_path.exists() and out_path.stat().st_size > 0:
                logger.info("MOSS-TTS API synthesized → %s", out_path.name)
                return {"success": True, "audio_path": str(out_path), "cached": False}
        except Exception as e:
            logger.error("MOSS-TTS API synthesis failed: %s", e)
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "MOSS-TTS API did not return audio."}

    async def _synthesize_cli(self, text: str) -> dict:
        if not self._dir:
            return {"success": False, "error": "MOSS-TTS directory ('tts.moss_dir') not configured."}
        
        cache_key = f"moss_cli:{self._ref_audio_path}:{self._prompt_text}"
        out_path = _cache_path(text, cache_key, ext=".wav")
        if out_path.exists():
            return {"success": True, "audio_path": str(out_path), "cached": True}

        cmd = [
            "python",
            str(Path(self._dir) / "infer_onnx.py"),
            "--text", text,
            "--output_path", str(out_path)
        ]
        if self._ref_audio_path:
            cmd.extend(["--prompt-audio-path", self._ref_audio_path])
        if self._prompt_text:
            cmd.extend(["--prompt-text", self._prompt_text])

        try:
            import subprocess
            loop = asyncio.get_event_loop()
            
            def _run_sub():
                logger.info("Running MOSS-TTS CLI command: %s", " ".join(cmd))
                res = subprocess.run(cmd, cwd=self._dir, capture_output=True, text=True, check=True)
                logger.info("MOSS-TTS CLI output: %s", res.stdout)
            
            await loop.run_in_executor(None, _run_sub)
            
            if out_path.exists() and out_path.stat().st_size > 0:
                logger.info("MOSS-TTS CLI synthesized → %s", out_path.name)
                return {"success": True, "audio_path": str(out_path), "cached": False}
        except Exception as e:
            logger.error("MOSS-TTS CLI synthesis failed: %s", e)
            return {"success": False, "error": str(e)}

        return {"success": False, "error": "MOSS-TTS CLI did not generate audio file."}



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
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for f in files[max_files:]:
                try:
                    f.unlink()
                except Exception:
                    pass
            logger.info("Cleaned TTS cache: kept %d most recent files", max_files)
        except Exception as exc:
            logger.warning("Failed to clean TTS cache: %s", exc)

    def _load_backend(self):
        preferred = config.get("tts.api", "edge")

        if preferred == "moss":
            try:
                return _MossTTS()
            except Exception as exc:
                logger.warning("MOSS-TTS init failed: %s", exc)

        if preferred == "kokoro":
            try:
                return _KokoroTTS()
            except Exception as exc:
                logger.warning("Kokoro TTS init failed: %s", exc)

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

        is_vi = is_vietnamese(text)
        backends_to_try = []

        # Định tuyến động dựa trên ngôn ngữ câu thoại thực tế
        if is_vi:
            # Tiếng Việt: Bỏ qua Kokoro vì Kokoro chỉ hỗ trợ Tiếng Anh
            if self._backend and self._backend.__class__.__name__ != "_KokoroTTS":
                backends_to_try.append(self._backend)
            
            # Đảm bảo EdgeTTS được thêm vào để đọc tiếng Việt
            if not self._edge_backend:
                try:
                    self._edge_backend = _EdgeTTS()
                except Exception:
                    pass
            if self._edge_backend and self._edge_backend not in backends_to_try:
                backends_to_try.append(self._edge_backend)
        else:
            # Tiếng Anh: Ưu tiên Kokoro trước (nếu được chọn làm mặc định)
            if self._backend and self._backend.__class__.__name__ == "_KokoroTTS":
                backends_to_try.append(self._backend)
            
            # Thêm EdgeTTS (EdgeTTS sẽ tự động dịch sang giọng en-US nhờ bộ lọc bên trong lớp _EdgeTTS)
            if not self._edge_backend:
                try:
                    self._edge_backend = _EdgeTTS()
                except Exception:
                    pass
            if self._edge_backend and self._edge_backend not in backends_to_try:
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

        for api in backends_to_try:
            try:
                result = await api.synthesize(text)
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
                    logger.warning("TTS api %s failed: %s", api.__class__.__name__, result.get("error"))
            except Exception as exc:
                logger.warning("TTS api %s raised exception: %s", api.__class__.__name__, exc)

        # Fallback cuối cùng: Stub mode (chỉ hiện chữ, không tiếng)
        return {
            "success":    True,
            "text":       text,
            "audio_path": None,
            "audio_url":  None,
            "duration_ms": 0,
            "stub":       True,
        }