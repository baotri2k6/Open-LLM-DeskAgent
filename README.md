<div align="center">

# 🎀 Open LLM DeskAgent

**AI companion sống trên desktop — nghe, nói, nhớ và điều khiển máy tính cùng mày.**

Được lấy cảm hứng từ Neuro-sama. Chạy hoàn toàn local.

![Version](https://img.shields.io/badge/version-0.2.0-purple?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-yellow?style=flat-square)
![Node](https://img.shields.io/badge/node-18+-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)

</div>

---

## Trông như thế nào?

Avatar Live2D **IceGirl** luôn hiện trên màn hình, kéo được, click để nói chuyện. Mỗi khi AI trả lời, avatar thay đổi biểu cảm theo nội dung — cười, ngạc nhiên, dỗi, vui — và giọng nói được clone từ mẫu âm thanh tùy chọn qua Fish Audio.

---

## Tính năng

<<<<<<< HEAD
|     | Tính năng              | Chi tiết                                                       |
| --- | ---------------------- | -------------------------------------------------------------- |
| 🎤  | **Voice conversation** | Nói chuyện bằng giọng — Whisper nhận dạng, AI trả lời bằng TTS |
| 🎭  | **Avatar Live2D**      | IceGirl với biểu cảm realtime theo từng câu AI nói             |
| 🗣️  | **Giọng anime**        | Fish Audio voice cloning · GPT-SoVITS · edge-tts fallback      |
| 🧠  | **Bộ nhớ**             | Nhớ thông tin về mày qua các cuộc trò chuyện                   |
| 💬  | **Tính cách**          | Neuro-sama style — lém lỉnh, hay trêu, ngắn gọn                |
| 📂  | **RAG tài liệu**       | Hỏi về PDF, DOCX, TXT của mày                                  |
| 🖥️  | **Desktop control**    | Mở app, đọc clipboard, tìm file                                |
| 👁️  | **Screen awareness**   | Screenshot + OCR, hỏi về lỗi đang hiện trên màn hình           |
| 🤖  | **Multi LLM**          | Ollama (local) · Gemini · OpenAI — đổi provider trong config   |
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
>>>>>>> f6ef09bc53661869a0ca38120c70b7df5e75184e

---

## Kiến trúc

```
┌─────────────────────────────────────┐
│         Electron Desktop App        │
│  Avatar Live2D · Chat UI · Tray     │
│  IPC · Hotkeys · Settings Window    │
└──────────────┬──────────────────────┘
               │ HTTP + WebSocket
               ▼
┌─────────────────────────────────────┐
│        Python AI Services           │
│                                     │
│  PlannerAgent ── MemoryAgent        │
│  VisionAgent  ── DesktopAgent       │
│                                     │
│  LLMService   STTService  TTSService│
│  RAG Pipeline ── ChromaDB           │
│  EmotionParser ── PersonaManager    │
└──────────────────────────────────────┘
```

---

## Cài đặt

### Yêu cầu

- Windows 10 / 11
- Python 3.10 – 3.12
- Node.js 18+
<<<<<<< HEAD
- [Ollama](https://ollama.com) _(nếu dùng LLM local)_
=======
- [Ollama](https://ollama.com) *(nếu dùng LLM local)*
>>>>>>> f6ef09bc53661869a0ca38120c70b7df5e75184e

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

### Bước 2 — Cài LLM (chọn 1 trong 3)

**Option A — Ollama (chạy local, miễn phí)**
<<<<<<< HEAD

```bash
# Cài Ollama tại https://ollama.com, sau đó:
ollama pull qwen2.5:1.5b
```

**Option B — Gemini (cần API key)**

```json
// config/companion.config.json
"llm": {
  "provider": "gemini",
  "gemini_api_key": "YOUR_KEY",
  "gemini_model": "gemini-2.5-flash"
}
```

**Option C — OpenAI**

```json
"llm": {
  "provider": "openai",
  "openai_api_key": "YOUR_KEY",
  "openai_model": "gpt-4o"
}
```

### Bước 3 — Cài giọng nói (tùy chọn)

**Fish Audio** — clone giọng anime từ sample của mày:

1. Đăng ký tại [fish.audio](https://fish.audio) → lấy API key
2. Upload ~30 giây audio → train model → copy Model ID
3. Điền vào config:

```json
"tts": {
  "backend": "fish_audio",
  "fish_audio_api_key": "YOUR_KEY",
  "fish_audio_model_id": "YOUR_MODEL_ID"
}
```

Nếu không dùng Fish Audio thì app tự fallback về `edge-tts` (giọng `vi-VN-HoaiMyNeural`).

### Bước 4 — Chạy

```bash
=======
```bash
# Cài Ollama tại https://ollama.com, sau đó:
ollama pull qwen2.5:1.5b
```

**Option B — Gemini (cần API key)**
```json
// config/companion.config.json
"llm": {
  "provider": "gemini",
  "gemini_api_key": "YOUR_KEY",
  "gemini_model": "gemini-2.5-flash"
}
```

**Option C — OpenAI**
```json
"llm": {
  "provider": "openai",
  "openai_api_key": "YOUR_KEY",
  "openai_model": "gpt-4o"
}
```

### Bước 3 — Cài giọng nói (tùy chọn)

**Fish Audio** — clone giọng anime từ sample của mày:

1. Đăng ký tại [fish.audio](https://fish.audio) → lấy API key
2. Upload ~30 giây audio → train model → copy Model ID
3. Điền vào config:

```json
"tts": {
  "backend": "fish_audio",
  "fish_audio_api_key": "YOUR_KEY",
  "fish_audio_model_id": "YOUR_MODEL_ID"
}
```

Nếu không dùng Fish Audio thì app tự fallback về `edge-tts` (giọng `vi-VN-HoaiMyNeural`).

### Bước 4 — Chạy

```bash
>>>>>>> f6ef09bc53661869a0ca38120c70b7df5e75184e
# Terminal 1: Ollama (nếu dùng local LLM)
ollama serve

# Terminal 2: App
venv\Scripts\activate
npm start
```

Avatar IceGirl xuất hiện góc dưới phải màn hình.

---

## Sử dụng

<<<<<<< HEAD
| Thao tác                 | Kết quả                      |
| ------------------------ | ---------------------------- |
| **Click vào avatar**     | Bắt đầu / dừng ghi âm        |
| **Space**                | Toggle ghi âm bật/tắt        |
| **Ctrl+Shift+Space**     | Ẩn / hiện avatar             |
| **Kéo avatar**           | Di chuyển trên màn hình      |
| **Chuột phải tray icon** | Menu: Settings / Hide / Quit |

---

## Cấu hình

Tất cả cấu hình nằm trong `config/companion.config.json`:

```json
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

Tất cả cấu hình nằm trong `config/companion.config.json`:

```json
{
  "llm": {
    "provider": "ollama",        // ollama | gemini | openai
    "model": "qwen2.5:1.5b"
  },
  "stt": {
    "model": "base",             // tiny | base | small | medium
    "language": "vi"
  },
  "tts": {
    "backend": "fish_audio",     // fish_audio | edge | pyttsx3
>>>>>>> f6ef09bc53661869a0ca38120c70b7df5e75184e
    "voice": "vi-VN-HoaiMyNeural"
  },
  "features": {
    "voice": true,
    "memory": true,
    "documentRag": true,
    "desktopControl": true,
<<<<<<< HEAD
    "screenAwareness": false // bật khi cần OCR màn hình
=======
    "screenAwareness": false     // bật khi cần OCR màn hình
>>>>>>> f6ef09bc53661869a0ca38120c70b7df5e75184e
  }
}
```

Tính cách của IceGirl chỉnh trong `python-services/persona/system_prompt.py`.

---

## Cấu trúc thư mục

```
Open-LLM-DeskAgent/
├── electron/               # Electron main process
│   ├── main.js             # Khởi động app, spawn Python
│   ├── preload.js          # Bridge renderer ↔ main
│   └── ipc/                # IPC handlers: ai, voice, avatar, system
├── renderer/               # Giao diện
│   ├── avatar.html         # Avatar window (Live2D)
│   ├── scripts/
│   │   ├── avatar-pet.js   # Logic avatar: drag, click, emotion
│   │   ├── avatar/         # live2d-manager, expression, lipsync, motion
│   │   ├── voice/          # recoder (WAV), audio-player
│   │   └── chat/           # chat-ui, history, message
│   └── styles/
├── python-services/        # Python AI backend
│   ├── main_server.py      # HTTP server, /chat /health /voice /tts
│   ├── agents/             # PlannerAgent, MemoryAgent, VisionAgent...
│   ├── services/           # LLM, STT, TTS, Memory
│   ├── persona/            # system_prompt, personality, emotion_engine
│   ├── emotion/            # emotion_classifier, mapper
│   ├── memory/             # short_term, long_term, chroma_store
│   ├── rag/                # PDF/DOCX/TXT loader, chunker, retriever
│   └── tools/              # open_app, clipboard, browser, web_search
├── assets/
│   └── live2d/IceGirl/     # Model Live2D, textures, expressions, motions
└── config/
    ├── companion.config.json
    ├── persona.config.json
    └── characters/icegirl.yaml
```

---

## Lỗi thường gặp

**Avatar hiện texture thô lúc đầu**
→ Bình thường — Live2D đang load. Chờ 2–3 giây.

**"Backend đang offline"**
→ Python server chưa chạy. Kiểm tra: `http://127.0.0.1:8765/health`

**AI không trả lời**
→ Với Ollama: đảm bảo `ollama serve` đang chạy và đã `ollama pull` model.

**Mic không nhận**
→ Lần đầu Windows hỏi quyền mic → bấm Cho phép.

**`faster-whisper` lần đầu chậm**
→ Đang tải model Whisper (~150MB). Những lần sau nhanh hơn.

---

## Roadmap

- [x] Avatar Live2D với biểu cảm realtime
- [x] Voice conversation (WAV → Whisper → LLM → TTS)
- [x] Fish Audio voice cloning
- [x] Emotion pipeline — parse emotion tag từ LLM output
- [x] Personality Neuro-sama style
- [x] Memory ngắn hạn + dài hạn
- [x] RAG tài liệu (PDF, DOCX, TXT)
- [x] Desktop control (mở app, clipboard, tìm file)
- [ ] Lipsync realtime theo biên độ âm thanh
- [ ] Screen awareness đầy đủ (OCR + hỏi về màn hình)
- [ ] Settings UI hoàn chỉnh
- [ ] Packaging Windows (.exe)

---

## Credits

- [Live2D Cubism SDK](https://www.live2d.com/en/sdk/about/) — avatar rendering
- [Open-LLM-VTuber](https://github.com/t41372/Open-LLM-VTuber) — tham khảo kiến trúc WAV recorder và TTS pipeline
- [Fish Audio](https://fish.audio) — voice cloning API
- [Ollama](https://ollama.com) — local LLM runtime
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — STT
- [edge-tts](https://github.com/rany2/edge-tts) — TTS fallback

---

<div align="center">
<sub>Dự án cá nhân · Không có cộng đồng hay support chính thức</sub>
</div>
