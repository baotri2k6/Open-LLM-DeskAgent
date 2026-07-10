"""Hotword Wake Word Detector — J.A.R.V.I.S.-like microphone monitoring.

Continuously listens to the mic, detects speech boundaries via RMS,
transcribes it with STTService, and triggers a callback when "icegirl" or "hello" is matched.
"""

from __future__ import annotations

import io
import math
import os
import wave
import time
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger("ai-companion.speech.hotword")


class HotwordDetector:
    """Listens to microphone using sounddevice and transcribes speech to match wake words."""

    def __init__(
        self,
        wake_words: list[str] = ["icegirl", "hello", "alo"],
        on_wake: Optional[Callable[[], None]] = None,
        sample_rate: int = 16000,
        energy_threshold: float = 0.03, # RMS threshold
        silence_seconds: float = 1.0,   # Seconds of silence to end utterance
    ) -> None:
        self.wake_words = [w.lower() for w in wake_words]
        self.on_wake = on_wake
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.silence_seconds = silence_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Load STT service early in constructor to cache the singleton instance
        try:
            from speech.stt.stt_service import STTService
            self.stt = STTService()
        except Exception as e:
            logger.error("HotwordDetector failed to load STTService: %s", e)
            self.stt = None


    def start(self) -> None:
        """Start monitoring in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("HotwordDetector: Started background thread ✓")

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("HotwordDetector: Stopped")

    def _run_loop(self) -> None:
        """Continuous record-and-transcribe loop."""
        import numpy as np
        try:
            import sounddevice as sd
        except Exception as e:
            logger.error("HotwordDetector: sounddevice not available: %s", e)
            return

        buffer = []
        in_utterance = False
        silence_start = 0.0
        last_status_log_time = 0.0

        def audio_callback(indata, frames, time_info, status):
            nonlocal in_utterance, silence_start, last_status_log_time
            if status:
                current_time = time.time()
                if current_time - last_status_log_time > 5.0:
                    logger.warning("HotwordDetector status: %s", status)
                    last_status_log_time = current_time

            # Compute Root Mean Square (RMS) energy
            rms = np.sqrt(np.mean(indata ** 2))

            if rms > self.energy_threshold:
                if not in_utterance:
                    in_utterance = True
                    logger.debug("HotwordDetector: Speech detected (RMS = %.3f)", rms)
                buffer.append(indata.copy())
                silence_start = time.time()
            elif in_utterance:
                buffer.append(indata.copy())
                if time.time() - silence_start > self.silence_seconds:
                    # Silence threshold reached, end of speech segment
                    in_utterance = False
                    self._process_utterance(buffer.copy())
                    buffer.clear()


        # Open stream with sounddevice
        try:
            # 1 channel, float32, blocksize = 0.1 seconds (1600 samples)
            blocksize = int(self.sample_rate * 0.1)
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                blocksize=blocksize,
                callback=audio_callback
            ):
                while self._running:
                    time.sleep(0.5)
        except Exception as exc:
            logger.warning(
                "HotwordDetector: Failed to initialize microphone stream. "
                "Ensure microphone is connected and not in exclusive use: %s", exc
            )
            # Standby/sleep fallback to prevent thread crashing
            while self._running:
                time.sleep(2.0)

    def _process_utterance(self, audio_chunks: list) -> None:
        """Save Numpy chunks to a temporary WAV and run transcription."""
        import numpy as np
        if not audio_chunks:
            return

        # Concatenate audio chunks
        audio_data = np.concatenate(audio_chunks, axis=0)

        # Convert float32 to int16 PCM bytes
        pcm_data = (audio_data * 32767.0).astype(np.int16).tobytes()

        # Write to memory WAV file
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2) # 16-bit
            wav.setframerate(self.sample_rate)
            wav.writeframes(pcm_data)

        wav_bytes = wav_buffer.getvalue()

        # Run STT transcription in a thread to keep streaming responsive
        threading.Thread(
            target=self._transcribe_and_check,
            args=(wav_bytes,),
            daemon=True
        ).start()

    def _transcribe_and_check(self, wav_bytes: bytes) -> None:
        try:
            if not self.stt or not self.stt.available:
                return

            import asyncio
            # Run async STT transcription synchronously in this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.stt.transcribe_bytes(wav_bytes))
            loop.close()


            if result.get("success"):
                text = result.get("text", "").lower().strip()
                if not text:
                    return

                logger.info("HotwordDetector transcribed: '%s'", text)

                # Check for wake words
                if any(w in text for w in self.wake_words):
                    logger.info("HotwordDetector MATCHED: Wake word detected! ✓")
                    if self.on_wake:
                        self.on_wake()
        except Exception as e:
            logger.error("HotwordDetector error during transcription: %s", e)
