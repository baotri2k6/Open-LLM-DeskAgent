"""Voice latency benchmark script - measures STT, LLM, and TTS latencies."""

import asyncio
import os
import struct
import tempfile
import time
import wave

import sys

from config.config import config
from speech.stt.stt_service import STTService
from llm.manager import LLMService
from speech.tts.tts_service import TTSService

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def generate_silent_wav(filepath: str, duration_sec: int = 1):
    sample_rate = 16000
    num_samples = sample_rate * duration_sec
    with wave.open(filepath, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for _ in range(num_samples):
            wav_file.writeframesraw(struct.pack("<h", 0))


async def run_benchmark():
    print("==================================================")
    print("Voice Latency Benchmark")
    print("==================================================")

    # Initialize services
    print("Initializing STT, LLM, and TTS services...")
    stt = STTService()
    llm = LLMService()
    tts = TTSService()

    # Create temporary silent wav file for STT testing
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        generate_silent_wav(tmp_path, duration_sec=1)

        # 1. Benchmark STT
        print("\n1. Benchmarking STT (Transcribing 1s of audio)...")
        t0 = time.perf_counter()
        stt_res = await stt.transcribe(tmp_path)
        t1 = time.perf_counter()
        stt_time = (t1 - t0) * 1000
        print(f"   STT Success: {stt_res.get('success', False)}")
        print(f"   STT Text: '{stt_res.get('text', '')}'")
        print(f"   STT Latency: {stt_time:.1f}ms")

        # 2. Benchmark LLM
        print("\n2. Benchmarking LLM (Generating chat response)...")
        prompt = "Chào bạn, hôm nay thế nào rồi? Trả lời thật ngắn gọn."
        t0 = time.perf_counter()
        llm_reply = await llm.chat(prompt)
        t1 = time.perf_counter()
        llm_time = (t1 - t0) * 1000
        print(f"   LLM Reply: '{llm_reply}'")
        print(f"   LLM Latency: {llm_time:.1f}ms")

        # 3. Benchmark TTS
        print("\n3. Benchmarking TTS (Synthesizing voice audio)...")
        speak_text = llm_reply or "Xin chào"
        t0 = time.perf_counter()
        tts_res = await tts.speak(speak_text)
        t1 = time.perf_counter()
        tts_time = (t1 - t0) * 1000
        print(f"   TTS Success: {tts_res.get('success', False)}")
        print(f"   TTS Audio URL: {tts_res.get('audio_url', '')}")
        print(f"   TTS Estimated Duration: {tts_res.get('duration_ms', 0)}ms")
        print(f"   TTS Latency: {tts_time:.1f}ms")

        # 4. Total Voice Latency
        total_time = stt_time + llm_time + tts_time
        print("\n==================================================")
        print(f"STT Latency:      {stt_time:8.1f}ms")
        print(f"LLM Latency:      {llm_time:8.1f}ms")
        print(f"TTS Latency:      {tts_time:8.1f}ms")
        print("--------------------------------------------------")
        print(f"Total Latency:    {total_time:8.1f}ms (to first audio chunk ready)")
        print("==================================================")

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


if __name__ == "__main__":
    asyncio.run(run_benchmark())
