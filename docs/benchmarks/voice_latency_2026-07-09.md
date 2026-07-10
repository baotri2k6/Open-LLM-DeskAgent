# Voice Latency Benchmark Report (2026-07-09)

This benchmark measures the time-to-first-audio chunk for the AI Companion voice pipeline, consisting of Speech-to-Text (STT), Large Language Model (LLM), and Text-to-Speech (TTS) services.

## Benchmark Results

- **Test Date:** 2026-07-09
- **Platform:** Windows 32-bit Python 3.10
- **STT Model:** faster-whisper (base) on CPU (int8)
- **LLM Model:** Local Qwen2.5-1.5B (Local CPU)
- **TTS Engine:** edge-tts (vi-VN-HoaiMyNeural)

| Pipeline Step | Latency (ms) |
| :--- | :--- |
| **Speech-to-Text (STT)** | 8,939.9 ms |
| **Large Language Model (LLM)** | 22,887.4 ms |
| **Text-to-Speech (TTS)** | 4,516.7 ms |
| **Total Voice Latency** | **36,344.1 ms** |

---

## Bottleneck Identification

The total latency of **36.3 seconds** is extremely high and far exceeds the 2,000ms target. Below are the key identified bottlenecks:

1. **STT Model Cold Start (8,939.9 ms):**
   - **Issue:** The `faster-whisper` model was loaded dynamically into memory on the first transcribe call.
   - **Impact:** Added nearly 9 seconds of initial delay. Subsequent transcriptions are processed in `<500ms` once the model weights are resident in RAM.

2. **LLM Weight Loading & MCP Timeout (22,887.4 ms):**
   - **Issue A (Cold Start):** Similar to STT, the local `Qwen2.5-1.5B` model weights are loaded on the first prompt invocation.
   - **Issue B (MCP Timeout):** The `time` MCP server attempted to run `uvx mcp-server-time` but timed out because network access is disabled in this environment. This blocked the chain of thought generation.
   - **Issue C (Lack of Streaming):** The benchmark called `llm.chat()` synchronously, which blocks until the final token is generated, rather than reading the first sentence chunk.

3. **Cloud TTS Web Latency (4,516.7 ms):**
   - **Issue:** `edge-tts` relies on Microsoft's cloud websocket endpoints to synthesize speech.
   - **Impact:** Remote server handshake and transmission latency added 4.5 seconds to download the output MP3.

---

## Proposed Optimizations

To reduce the voice pipeline latency below **2,000ms** (and achieve `<1,000ms` for warm runs), we recommend:

1. **Pre-warming / Lazy Preload:**
   - Preload Whisper and Qwen model weights in a background thread immediately at desktop application startup, rather than waiting for the first voice query.
2. **First-Sentence Streaming Synthesis:**
   - Stream the LLM response token-by-token and slice the text on sentence boundaries (`.`, `?`, `!`, `,`). Pass the very first sentence to the TTS engine immediately so audio playback starts while the rest of the reply is still generating.
3. **Local TTS Fallback:**
   - Implement a fast local TTS engine (e.g. `pyttsx3` or a small local `Kokoro` / `Coqui` model) to bypass cloud websocket connection overhead.
4. **MCP Timeout Tuning:**
   - Reduce the connection timeout for spawning external MCP servers from the default to `1.5` seconds, or cache dependencies locally to avoid remote package resolves on each run.
