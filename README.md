<div align="center">

# 🎀 Open LLM DeskAgent

**AI companion sống trên desktop — nghe, nói, nhớ, cảm xúc và tự suy nghĩ.**

Lấy cảm hứng từ Neuro-sama. Chạy local hoàn toàn.

![Version](https://img.shields.io/badge/version-0.2.0-purple?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-yellow?style=flat-square)
![Node](https://img.shields.io/badge/node-18+-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)

</div>

---

## Trông như thế nào?

M��t avatar Live2D luôn hiện trên màn hình, kéo được, click để nói chuyện. Mỗi khi AI trả lời, avatar thay đổi biểu cảm theo từng câu — cười, ngạc nhiên, dỗi, vui — miệng chuyển động theo âm thanh. AI tự nhớ thông tin về mày, thay đổi tâm trạng theo thời gian, và chủ động lên tiếng khi thấy mày im lặng quá lâu.

---

## Tính năng

| | Tính năng | Chi tiết |
|---|---|---|
| 🧠 | **Cognitive Loop** | Perception → Memory → Emotion → Cognition → Action, chạy liên tục |
| 🎭 | **Multi-character** | IceGirl · Hiyori · Mao · Huohuo — mỗi nhân vật có tính cách và biểu cảm riêng |
| 🎤 | **Voice conversation** | Mic → Whisper STT → LLM → TTS phát gối đầu từng câu |
| 🔊 | **Giọng anime** | Fish Audio voice cloning · GPT-SoVITS local · edge-tts fallback |
| 💬 | **Streaming response** | LLM stream token, TTS tổng hợp song song theo từng câu |
| 😊 | **Emotion realtime** | LLM nhúng `[happy]`, `[wink]`... → Live2D thay expression ngay lập tức |
| 👄 | **Lipsync** | Web Audio API phân tích amplitude → drive `ParamMouthOpenY` |
| 🧠 | **Bộ nhớ đầy đủ** | Short-term hội thoại + Long-term ChromaDB + write-back tự động |
| 💞 | **Relationship system** | Điểm quan hệ tăng theo tương tác, ảnh hưởng cách nói chuyện |
| 🌡️ | **Mood drift** | Tâm trạng thay đổi theo thời gian idle và nội dung hội thoại |
| 🤖 | **Autonomous loop** | Tự nhận xét màn hình, tự phá vỡ im lặng khi idle > 30 giây |
| 📂 | **RAG tài liệu** | Import PDF, DOCX, TXT — hỏi trực tiếp nội dung tài liệu |
| 🖥️ | **Desktop control** | Mở app, đọc clipboard, tìm file, tự động hóa |
| 👁️ | **Screen awareness** | Screenshot + OCR, hỏi về nội dung đang hiện trên màn hình |
| 🎮 | **Twitch mode** | Đọc Twitch chat, tự comment vào tin nhắn của viewer |
| 🤖 | **Multi LLM** | Ollama local · Gemini · OpenAI — đổi provider bằng `/model` chat command |

---

## Kiến trúc

```
┌─────────────────────────────────────────────────────┐
│                Electron Desktop App                  │
│  Avatar Live2D · Chat UI · Settings · Tray          │
│  IPC · Hotkeys · Overlay window                     │
└────────────────────────┬────────────────────────────┘
                         │ HTTP chunked streaming
                         ▼
┌─────────────────────────────────────────────────────┐
│            Python AI Services (HTTP :8765)           │
│                                                      │
│  ┌─────────────── Cognitive Loop ─────────────────┐ │
│  │  PerceptionFusion  ←  Voice / Text / Screen    │ │
│  │         ↓                                       │ │
│  │  MemoryManager     ←  Short + Long + Relation  │ │
│  │         ↓                                       │ │
│  │  EmotionEvaluator  ←  Mood + PersonaFilter     │ │
│  │         ↓                                       │ │
│  │  CognitionEngine   →  LLM stream + EmotionTag  │ │
│  │         ↓                                       │ │
│  │  Action: TTS · Expression · Desktop · Memory   │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  Autonomous Loop · Twitch Loop (background threads)  │
│  RAG Pipeline · ChromaDB · STT · TTS Cache          │
└─────────────────────────────────────────────────────┘
```

---

## Nhân vật

| Nhân vật | Tính cách | Model |
|---|---|---|
| **IceGirl** | Neuro-sama style — lém lỉnh, trêu chọc, tự tin thái quá | `assets/live2d/IceGirl/` |
| **Hiyori** | Nữ sinh năng động, cổ vũ nhiệt tình, luôn tươi cười | `assets/live2d/hiyori_en/` |
| **Mao** | Tsundere thời trang, sắc sảo, hay châm chọc nhẹ | `assets/live2d/mao_en/` |
| **Huohuo** | Phán quan nhút nhát từ HSR, sợ ma nhưng trách nhiệm | `assets/live2d/huohuo2/` |

Đổi nhân vật trong Settings hoặc chỉnh `avatarModel` trong `config/companion.config.json`.

---

## Cài đặt

### Yêu cầu

- Windows 10 / 11
- Python 3.10 – 3.12
- Node.js 18+
- [Ollama](https://ollama.com) *(nếu dùng LLM local)*

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

**Option A — Ollama (local, miễn phí, recommend)**
```bash
# Cài Ollama tại https://ollama.com
ollama pull qwen2.5:1.5b
```

**Option B — Gemini API**

Vào `config/companion.config.json`, sửa:
```json
"llm": {
  "provider": "gemini",
  "gemini_api_key": "AIza...",
  "gemini_model": "gemini-2.5-flash"
}
```

**Option C — OpenAI API**
```json
"llm": {
  "provider": "openai",
  "openai_api_key": "sk-...",
  "openai_model": "gpt-4o-mini"
}
```

Hoặc đổi provider ngay trong chat: `/model ollama`, `/model gemini`, `/model openai`

### Bước 3 — Cài giọng nói (tùy chọn)

**Fish Audio** — clone giọng anime từ sample của mày:

1. Đăng ký tại [fish.audio](https://fish.audio) → API Keys → tạo key
2. Upload 15–30 giây audio anime/VTuber → Create Model → copy Model ID
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
# Terminal 1: Ollama (nếu dùng local LLM)
ollama serve

# Terminal 2: App
venv\Scripts\activate
npm start
```

---

## Sử dụng

| Thao tác | Kết quả |
|---|---|
| **Click avatar** | Bắt đầu / dừng ghi âm |
| **Space** | Toggle ghi âm |
| **Ctrl+Shift+Space** | Ẩn / hiện avatar |
| **Kéo avatar** | Di chuyển trên màn hình |
| **Chuột phải tray** | Settings / Hide / Quit |

### Chat commands

| Lệnh | Tác dụng |
|---|---|
| `/model ollama` | Chuyển sang Ollama local |
| `/model gemini` | Chuyển sang Gemini API |
| `/model openai` | Chuyển sang OpenAI |
| `/stt tiny` | Đổi Whisper model (tiny/base/small) |
| `/sit` | Avatar ngồi xuống |
| `/stand` | Avatar đứng lên |
| `/mic` | Toggle mic prop |

---

## Cấu hình

`config/companion.config.json`:

```json
{
  "app": {
    "avatarModel": "assets/live2d/IceGirl/IceGirl.model3.json",
    "interactionMode": "streamer"
  },
  "llm": {
    "provider": "ollama",
    "model": "qwen2.5:1.5b"
  },
  "stt": { "model": "tiny", "language": "vi" },
  "tts": {
    "backend": "fish_audio",
    "fish_audio_api_key": "",
    "fish_audio_model_id": ""
  },
  "features": {
    "voice": true,
    "memory": true,
    "documentRag": true,
    "screenAwareness": false,
    "twitchMode": false
  }
}
```

---

## Cấu trúc thư mục

```
Open-LLM-DeskAgent/
├── electron/
│   ├── main.js                  # Khởi động app, spawn Python, hotkeys
│   ├── preload.js               # Bridge renderer ↔ main process
│   └── ipc/                     # ai, voice, avatar, system handlers
├── renderer/
│   ├── avatar.html              # Avatar window (Live2D)
│   ├── settings.html            # Settings UI
│   └── scripts/
│       ├── avatar-pet.js        # Logic avatar: drag, click, emotion, lipsync
│       ├── avatar/              # live2d-manager, expression, lipsync, motion
│       ├── voice/               # recoder (WAV PCM16), audio-player
│       └── chat/                # chat-ui, history, message
├── python-services/
│   ├── main_server.py           # HTTP server + Cognitive Loop + Autonomous Loop
│   ├── core/
│   │   ├── cognition.py         # Tầng 4: LLM Reasoning + EmotionStreamParser
│   │   ├── perception_fusion.py # Tầng 1: Gom inputs → ContextPacket
│   │   ├── emotion_parser.py    # Parse [emotion] tags từ LLM stream
│   │   └── event_bus.py        # In-process pub/sub event bus
│   ├── agents/                  # PlannerAgent, MemoryAgent, VisionAgent...
│   ├── services/                # LLM (Ollama/Gemini/OpenAI), STT, TTS, Memory
│   ├── persona/                 # system_prompt, personality, characters YAML
│   ├── memory/                  # short_term, long_term, chroma_store
│   ├── emotion/                 # emotion_classifier, emotion_mapper
│   ├── rag/                     # PDF/DOCX/TXT loader, chunker, retriever
│   └── tools/                   # open_app, clipboard, browser, web_search
├── assets/
│   └── live2d/
│       ├── IceGirl/
│       ├── hiyori_en/
│       ├── mao_en/
│       └── huohuo2/
└── config/
    ├── companion.config.json
    ├── persona.config.json
    └── characters/              # icegirl.yaml, hiyori.yaml, mao.yaml, huohuo.yaml
```

---

## Lỗi thường gặp

**Avatar hiện texture thô lúc đầu**
→ Live2D đang load. Chờ 2–3 giây, sẽ tự chuyển sang nhân vật hoàn chỉnh.

**"Backend đang offline"**
→ Python server chưa chạy. Kiểm tra: `http://127.0.0.1:8765/health`

**AI không trả lời / Ollama error**
→ Đảm bảo `ollama serve` đang chạy và đã `ollama pull qwen2.5:1.5b`.

**Mic không nhận**
→ Windows hỏi quyền mic lần đầu → bấm **Cho phép**.

**Fish Audio không phát âm**
→ Kiểm tra API key và Model ID trong Settings hoặc config. App tự fallback về edge-tts nếu lỗi.

**`faster-whisper` lần đầu chậm**
→ Đang tải Whisper model (~150MB). Những lần sau cache lại, nhanh hơn nhiều.

---

## Roadmap

- [x] Avatar Live2D với biểu cảm + lipsync realtime
- [x] Voice conversation — WAV PCM16 → Whisper → LLM → TTS per-sentence
- [x] Fish Audio voice cloning + GPT-SoVITS local
- [x] Cognitive loop 4 tầng — Perception → Memory → Emotion → Cognition
- [x] Emotion pipeline — LLM nhúng tag → Live2D expression realtime
- [x] Multi-character (IceGirl / Hiyori / Mao / Huohuo)
- [x] Memory đầy đủ — short-term + long-term ChromaDB + write-back
- [x] Relationship system + Mood drift
- [x] Autonomous loop — tự comment màn hình, tự phá im lặng
- [x] Twitch mode — đọc chat, tự comment viewer
- [x] RAG tài liệu (PDF, DOCX, TXT)
- [x] Desktop control + Screen awareness (OCR)
- [x] Settings UI đầy đủ, đổi config live trong app
- [ ] Packaging Windows (.exe) với electron-builder
- [ ] Memory UI — xem, sửa, xóa ký ức trong app
- [ ] Multi-monitor support

---

## Credits

- [Live2D Cubism SDK](https://www.live2d.com/en/sdk/about/) — avatar rendering
- [Open-LLM-VTuber](https://github.com/t41372/Open-LLM-VTuber) — tham khảo WAV recorder và TTS pipeline
- [Fish Audio](https://fish.audio) — voice cloning API
- [Ollama](https://ollama.com) — local LLM runtime
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — STT
- [edge-tts](https://github.com/rany2/edge-tts) — TTS fallback
- [ChromaDB](https://www.trychroma.com) — vector store cho long-term memory

---

<div align="center">
<sub>Dự án cá nhân · Không có cộng đồng hay support chính thức</sub>
</div>
