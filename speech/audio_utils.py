"""Audio utility functions for STT and TTS parsing."""

from __future__ import annotations

import io
import wave


def create_mock_wav(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Create basic empty wave format bytes for testing speech components."""
    num_samples = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)  # Mono
        wav.setsampwidth(2)   # 16-bit PCM
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00" * (num_samples * 2))
    return buffer.getvalue()


def is_valid_wav_header(wav_bytes: bytes) -> bool:
    """Validate if given bytes contain a valid WAV header."""
    return wav_bytes.startswith(b"RIFF") and b"WAVE" in wav_bytes[:16]
