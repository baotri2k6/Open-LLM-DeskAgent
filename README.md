<div align="center">

# 🎀 Open LLM DeskAgent

**AI companion sống trên desktop — nghe, nói, nhớ, cảm xúc và tự suy nghĩ.**

Lấy cảm hứng từ Neuro-sama. Chạy hoàn toàn local trên Windows.

![Version](https://img.shields.io/badge/version-0.2.0-purple?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-yellow?style=flat-square)
![Node](https://img.shields.io/badge/node-18+-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)

</div>

---

## Giới thiệu

**Open LLM DeskAgent** là AI companion desktop với avatar Live2D luôn hiện trên màn hình. Nhân vật tự nghe giọng nói, trả lời bằng giọng anime clone, thay đổi biểu cảm theo từng câu, nhớ thông tin về mày qua nhiều ngày, và chủ động lên tiếng khi thấy mày im lặng quá lâu.

Không phải chatbot. Không phải assistant. Là một người bạn ảo thực sự sống trên máy tính.

---

## Tính năng

<<<<<<< HEAD
| | Tính năng | Chi tiết |
| --- | ---------------------- | -------------------------------------------------------------- |
| 🎤 | **Voice conversation** | Nói chuyện bằng giọng — Whisper nhận dạng, AI trả lời bằng TTS |
| 🎭 | **Avatar Live2D** | IceGirl với biểu cảm realtime theo từng câu AI nói |
| 🗣️ | **Giọng anime** | Fish Audio voice cloning · GPT-SoVITS · edge-tts fallback |
| 🧠 | **Bộ nhớ** | Nhớ thông tin về mày qua các cuộc trò chuyện |
| 💬 | **Tính cách** | Neuro-sama style — lém lỉnh, hay trêu, ngắn gọn |
| 📂 | **RAG tài liệu** | Hỏi về PDF, DOCX, TXT của mày |
| 🖥️ | **Desktop control** | Mở app, đọc clipboard, tìm file |
| 👁️ | **Screen awareness** | Screenshot + OCR, hỏi về lỗi đang hiện trên màn hình |
| 🤖 | **Multi LLM** | Ollama (local) · Gemini · OpenAI — đổi provider trong config |
=======
| | Tính năng | Chi tiết |
|---|---|---|
| 🎤 | **Voice conversation** | Nói chuyện bằng giọng — Whisper nhận dạng, AI trả lời bằng TTS |
| 🎭 | **Avatar Live2D** | IceGirl với biểu cảm realtime theo từng câu AI nói |
| 🗣️ | **Giọng anime** | Fish Audio voice cloning · GPT-SoVITS · edge-tts fallback |
| 🧠 | **Bộ nhớ** | Nhớ thông tin về mày qua các cuộc trò chuyện |
| 💬 | **Tính cách** | Neuro-sama style — lém lỉnh, hay trêu, ngắn gọn |
| 📂 | **RAG tài liệu** | Hỏi về PDF, DOCX, TXT của mày |
| 🖥️ | **Desktop control** | Mở app, đọc clipboard, tìm file |
| 👁️ | **Screen awareness** | Screenshot + OCR, hỏi về lỗi đang hiện trên màn hình |
| 🤖 | **Multi LLM** | Ollama (local) · Gemini · OpenAI — đổi provider trong config |

> > > > > > > f6ef09bc53661869a0ca38120c70b7df5e75184e

---

## Kiến trúc

```
┌──────────────────────────────────────────────────────────────┐
│                    Electron Desktop App                       │
│  Avatar Live2D · Chat UI · Settings · Tray · Hotkeys         │
│  IPC: ai, voice, avatar, system                              │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP chunked streaming (:8765)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                  Python AI Services                           │
│                                                              │
│  ┌─────────────── Cognitive Loop ────────────────────────┐  │
│  │  ① Perception  ← Voice / Text / Screen / Time        │  │
│  │       ↓  PerceptionFusion → ContextPacket             │  │
│  │  ② Memory      ← Short-term + ChromaDB + Relation    │  │
│  │       ↓  Recall facts, mood, rel_level                │  │
│  │  ③ Emotion     ← MoodDrift + PersonaFilter           │  │
│  │       ↓  Build system prompt với tính cách nhân vật  │  │
│  │  ④ Cognition   → LLM stream + EmotionTag parser      │  │
│  │       ↓                                               │  │
│  │  ⑤ Action: TTS · Expression · Desktop · Memory       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Agent Loop · Autonomous Loop · Twitch Loop (background)     │
│  RAG Pipeline · ChromaDB · STT · TTS Cache                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Cài đặt

### Yêu cầu

- Windows 10 / 11
- Python 3.10 – 3.12
- Node.js 18+
  <<<<<<< HEAD
- # [Ollama](https://ollama.com) _(nếu dùng LLM local)_
- [Ollama](https://ollama.com) _(nếu dùng LLM local)_
  > > > > > > > f6ef09bc53661869a0ca38120c70b7df5e75184e

### Bước 1 — Clone và cài dependencies

```bash
git clone https://github.com/username/Open-LLM-DeskAgent.git
cd Open-LLM-DeskAgent

# Python
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Node
npm install
```

### Bước 2 — Cài LLM

**Option A — Ollama (chạy local, miễn phí)**
<<<<<<< HEAD

```bash
# Cài tại https://ollama.com, sau đó:
ollama pull qwen2.5:1.5b
```

**Option B — Gemini (cần API key)**

Vào `config/companion.config.json`, sửa:

```json
"llm": {
  "provider": "gemini",
  "gemini_api_key": "AIza...",
  "gemini_model": "gemini-2.5-flash"
}
```

**Option C — OpenAI**

```json
"llm": {
  "provider": "openai",
  "openai_api_key": "sk-...",
  "openai_model": "gpt-4o-mini"
}
```

### Bước 3 — Cài giọng anime (tùy chọn)

### Bước 3 — Cài giọng nói (tùy chọn)

**Fish Audio** — clone giọng anime từ sample của mày:

1. Đăng ký tại [fish.audio](https://fish.audio) → API Keys → tạo key
2. Upload 15–30 giây audio anime/VTuber → **Create Model** → copy **Model ID**
3. Điền vào config:

```json
"tts": {
  "backend": "fish_audio",
  "fish_audio_api_key": "YOUR_KEY",
  "fish_audio_model_id": "YOUR_MODEL_ID"
}
```

Nếu không dùng Fish Audio thì tự fallback về `edge-tts`.

### Bước 4 — Chạy

```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: App
venv\Scripts\activate
npm start
```

---

## Sử dụng

<<<<<<< HEAD
| Thao tác | Kết quả |
| ------------------------ | ---------------------------- |
| **Click vào avatar** | Bắt đầu / dừng ghi âm |
| **Space** | Toggle ghi âm bật/tắt |
| **Ctrl+Shift+Space** | Ẩn / hiện avatar |
| **Kéo avatar** | Di chuyển trên màn hình |
| **Chuột phải tray icon** | Menu: Settings / Hide / Quit |

---

## Cấu hình

Tất cả cấu hình nằm trong `config/companion.config.json`:

````json
{
  "llm": {
    "provider": "ollama", // ollama | gemini | openai
    "model": "qwen2.5:1.5b"
  },
  "stt": {
    "model": "base", // tiny | base | small | medium
    "language": "vi"
  },
  "tts": {
    "backend": "fish_audio", // fish_audio | edge | pyttsx3
=======
| Thao tác | Kết quả |
|---|---|
| **Click vào avatar** | Bắt đầu / dừng ghi âm |
| **Space** | Toggle ghi âm bật/tắt |
| **Ctrl+Shift+Space** | Ẩn / hiện avatar |
| **Kéo avatar** | Di chuyển trên màn hình |
| **Chuột phải tray icon** | Menu: Settings / Hide / Quit |

---

## Cấu hình

`config/companion.config.json`:

```json
{
  "app": {
    "avatarModel": "assets/live2d/IceGirl/IceGirl.model3.json",
    "interactionMode": "assistant"
  },
  "llm": {
    "provider": "ollama",
    "model": "qwen2.5:1.5b",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini"
  },
  "stt": { "model": "tiny", "language": "vi" },
  "tts": {
    "backend": "fish_audio",
    "fish_audio_api_key": "",
    "fish_audio_model_id": "",
    "voice": "vi-VN-HoaiMyNeural"
  },
  "features": {
    "voice": true,
    "memory": true,
    "documentRag": true,
    "desktopControl": true,
    "screenAwareness": false,
    "twitchMode": false
  }
}
```

Tất cả config có thể chỉnh trong **Settings window** mà không cần restart.

---

## Cấu trúc thư mục

```
Open-LLM-DeskAgent/
├── electron/
│   ├── main.js                    # Khởi động app, spawn Python, hotkeys, mic permission
│   ├── preload.js                 # Bridge window.companion API cho renderer
│   └── ipc/                       # ai, voice, avatar, system handlers
├── renderer/
│   ├── avatar.html                # Avatar window (Live2D, transparent, always-on-top)
│   ├── settings.html              # Settings UI với real save/load
│   └── scripts/
│       ├── avatar-pet.js          # Logic: drag, click, voice, lipsync, emotion, accessory
│       ├── avatar/                # live2d-manager, expression, lipsync, motion
│       ├── voice/                 # recoder (WAV PCM16), audio-player
│       └── chat/                  # chat-ui, history, message
├── python-services/
│   ├── main_server.py             # HTTP server + Cognitive Loop + Autonomous + Twitch
│   ├── core/
│   │   ├── cognition.py           # LLM Reasoning + EmotionStreamParser
│   │   ├── perception_fusion.py   # Gom inputs → ContextPacket
│   │   ├── emotion_parser.py      # Parse [emotion] tags từ stream
│   │   └── event_bus.py           # In-process pub/sub
│   ├── agents/                    # PlannerAgent, MemoryAgent, VisionAgent, DesktopAgent
│   ├── services/
│   │   ├── llm_service.py         # Ollama/Gemini/OpenAI + Agent Loop + Tool Calling
│   │   ├── tts_service.py         # Fish Audio / GPT-SoVITS / Kokoro / edge-tts / pyttsx3
│   │   ├── stt_service.py         # faster-whisper
│   │   └── memory_service.py      # Short-term + Long-term + relationship + mood
│   ├── persona/                   # system_prompt.py + 4 character YAML files
│   ├── memory/                    # ChromaDB vector store, short_term, long_term
│   ├── rag/                       # PDF/DOCX/TXT loader, chunker, retriever
│   └── tools/                     # computer_control, file_reader, file_writer, browser, screen
├── assets/
│   └── live2d/
│       ├── IceGirl/
│       ├── hiyori_en/
│       ├── mao_en/
│       └── huohuo2/
└── config/
    ├── companion.config.json
    ├── persona.config.json
    └── characters/                # icegirl.yaml, hiyori.yaml, mao.yaml, huohuo.yaml
```

---

## Lỗi thường gặp

**Avatar hiện texture rời rạc lúc đầu**
→ Live2D đang load. Chờ 2–3 giây sẽ tự chuyển thành nhân vật hoàn chỉnh.

**"Backend đang offline"**
→ Python server chưa chạy. Kiểm tra: `http://127.0.0.1:8765/health`

**AI không trả lời / Ollama lỗi**
→ Đảm bảo `ollama serve` đang chạy và đã `ollama pull qwen2.5:1.5b`.

**Mic không nhận**
→ Windows hỏi quyền mic lần đầu → bấm **Cho phép**.

**STT nhận dạng sai nhiều**
→ Gõ `/stt base` hoặc `/stt small` để dùng model lớn hơn, chính xác hơn.

**Fish Audio không có tiếng**
→ Kiểm tra API key và Model ID trong Settings. App tự fallback về edge-tts nếu lỗi.

**`faster-whisper` lần đầu chậm**
→ Đang tải Whisper model (~150MB). Những lần sau đã cache, nhanh hơn.

---

## Roadmap

- [x] Avatar Live2D với biểu cảm + lipsync realtime
- [x] Voice conversation — WAV PCM16 → Whisper → LLM → TTS per-sentence
- [x] VAD + Barge-in + ASR streaming draft
- [x] Fish Audio voice cloning + GPT-SoVITS + Kokoro offline
- [x] Cognitive loop 4 tầng — Perception → Memory → Emotion → Cognition
- [x] Emotion pipeline — LLM nhúng tag → Live2D expression realtime
- [x] 4 nhân vật + accessory system per-model
- [x] Memory đầy đủ — short-term + long-term ChromaDB + write-back
- [x] Relationship system + Mood drift
- [x] Agent loop + Tool calling native (Ollama / Gemini / OpenAI)
- [x] Approval flow cho hành động nguy hiểm
- [x] Autonomous loop — tự nói, tự nhận xét màn hình
- [x] Twitch mode — đọc chat, tự comment viewer
- [x] RAG tài liệu (PDF, DOCX, TXT)
- [x] Desktop control + Screen awareness (OCR)
- [x] Settings UI đầy đủ, đổi config live trong app
- [ ] Packaging Windows (.exe) với electron-builder
- [ ] Memory UI — xem, sửa, xóa ký ức trong app

---

## Credits

- [Live2D Cubism SDK](https://www.live2d.com/en/sdk/about/) — avatar rendering
- [Open-LLM-VTuber](https://github.com/t41372/Open-LLM-VTuber) — tham khảo WAV recorder và TTS pipeline
- [Fish Audio](https://fish.audio) — voice cloning API
- [Kokoro TTS](https://github.com/hexgrad/kokoro) — offline neural TTS
- [Ollama](https://ollama.com) — local LLM runtime
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — STT
- [edge-tts](https://github.com/rany2/edge-tts) — TTS fallback
- [ChromaDB](https://www.trychroma.com) — vector store cho long-term memory

---

<div align="center">
<sub>Dự án cá nhân · Nguyễn Bảo Trí</sub>
</div>
````
