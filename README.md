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

| | Tính năng | Mô tả |
|---|---|---|
| 🧠 | **Cognitive Loop** | Perception → Memory → Emotion → Cognition → Action — vòng lặp nhận thức liên tục |
| 🎭 | **4 nhân vật Live2D** | IceGirl · Hiyori · Mao · Huohuo — tính cách, biểu cảm và phụ kiện riêng |
| 🎤 | **Voice conversation** | VAD → STT → LLM → TTS phát gối đầu từng câu |
| ⚡ | **Barge-in** | Ngắt AI đang nói, nói đè lên — AI dừng ngay lập tức |
| 📝 | **ASR streaming** | Nhận dạng giọng nói realtime trong lúc đang nói |
| 🔊 | **Giọng anime** | Fish Audio clone · GPT-SoVITS local · Kokoro offline · edge-tts fallback |
| 😊 | **Emotion realtime** | LLM nhúng `[happy]` `[wink]`... → Live2D thay expression ngay lập tức |
| 👄 | **Lipsync** | Web Audio API phân tích amplitude → drive miệng Live2D |
| 🧠 | **Bộ nhớ đầy đủ** | Short-term hội thoại + Long-term ChromaDB + write-back sau mỗi turn |
| 💞 | **Relationship system** | Điểm quan hệ tăng qua tương tác, ảnh hưởng cách nói chuyện |
| 🌡️ | **Mood drift** | Tâm trạng thay đổi theo thời gian idle và nội dung hội thoại |
| 🤖 | **Autonomous loop** | Tự nhận xét màn hình, tự phá vỡ im lặng khi idle > 30 giây |
| 🛠️ | **Agent + Tool Calling** | Mở app, chạy lệnh, ghi file, điều khiển chuột/bàn phím, tìm Google |
| 🔒 | **Approval flow** | Hành động nguy hiểm cần xác nhận trước khi chạy |
| 📂 | **RAG tài liệu** | Import PDF, DOCX, TXT — hỏi trực tiếp nội dung tài liệu |
| 👁️ | **Screen awareness** | Screenshot + OCR, hỏi về nội dung đang hiện trên màn hình |
| 🎮 | **Twitch mode** | Đọc Twitch chat, tự comment vào tin nhắn viewer |
| 🔀 | **Multi LLM** | 7 provider — Ollama · Gemini · OpenAI · DeepSeek · GLM · Qwen · Custom |

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

## Nhân vật

| Nhân vật | Tính cách | Phụ kiện |
|---|---|---|
| **IceGirl** | Neuro-sama style — lém lỉnh, trêu chọc, tự tin thái quá | Tay cầm, tai mèo, vương miện, cánh, tai nghe, tóc |
| **Hiyori** | Nữ sinh năng động, cổ vũ nhiệt tình, luôn tươi cười | — |
| **Mao** | Tsundere thời trang, sắc sảo, hay châm chọc nhẹ | 8 expression preset |
| **Huohuo** | Phán quan nhút nhát từ Honkai Star Rail, sợ ma nhưng trách nhiệm | Gối ôm, lá cờ |

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

### Bước 2 — Cài LLM

M�� `config/companion.config.json` và chỉnh `llm.provider` + key tương ứng:

**Ollama (local, miễn phí — khuyến nghị):**
```bash
ollama pull qwen2.5:1.5b
```
```json
"llm": { "provider": "ollama", "model": "qwen2.5:1.5b" }
```

**Gemini (miễn phí quota hàng ngày, chất lượng cao):**
```json
"llm": { "provider": "gemini", "gemini_api_key": "AIza...", "gemini_model": "gemini-2.5-flash" }
```

**OpenAI:**
```json
"llm": { "provider": "openai", "openai_api_key": "sk-...", "openai_model": "gpt-4o-mini" }
```

**DeepSeek:**
```json
"llm": { "provider": "deepseek", "deepseek_api_key": "sk-...", "deepseek_model": "deepseek-chat" }
```

**Zhipu GLM:**
```json
"llm": { "provider": "glm", "glm_api_key": "...", "glm_model": "glm-4" }
```

**DashScope Qwen:**
```json
"llm": { "provider": "qwen", "qwen_api_key": "...", "qwen_model": "qwen-plus" }
```

**OpenAI-Compatible (LM Studio, vLLM, llama.cpp...):**
```json
"llm": {
  "provider": "openai-compatible",
  "openai_compatible_base_url": "http://localhost:8000/v1",
  "openai_compatible_api_key": "none",
  "openai_compatible_model": "llama3"
}
```

### Bước 3 — Cài STT

**Whisper (mặc định):** Tự tải khi chạy lần đầu (~150MB).

**FunASR (nhanh hơn, đa ngôn ngữ):**
```bash
pip install funasr modelscope torchaudio
```
```json
"stt": { "model": "funasr", "funasr_model": "iic/SenseVoiceSmall" }
```

### Bước 4 — Cài giọng anime (tùy chọn)

**Fish Audio** — clone giọng từ sample:
1. Đăng ký tại [fish.audio](https://fish.audio) → API Keys → tạo key
2. Upload 15–30 giây audio anime/VTuber → **Create Model** → copy **Model ID**
3. Điền vào config:
```json
"tts": { "backend": "fish_audio", "fish_audio_api_key": "YOUR_KEY", "fish_audio_model_id": "YOUR_ID" }
```

**Kokoro TTS (offline, không cần internet):**
```bash
pip install kokoro soundfile
```
```json
"tts": { "backend": "kokoro" }
```

**GPT-SoVITS (local voice cloning):**
```json
"tts": {
  "backend": "gpt_sovits",
  "gpt_sovits_api_url": "http://127.0.0.1:9880/tts",
  "gpt_sovits_ref_audio_path": "path/to/reference.wav",
  "gpt_sovits_prompt_text": "Nội dung audio tham chiếu"
}
```

Không cấu hình → tự fallback về `edge-tts` giọng `vi-VN-HoaiMyNeural`.

### Bước 5 — Chạy

```bash
# Terminal 1: Ollama (nếu dùng local LLM)
ollama serve

# Terminal 2: App
venv\Scripts\activate
npm start
```

---

## Sử dụng

### Thao tác cơ bản

| Thao tác | Kết quả |
|---|---|
| **Click avatar** | Phản ứng theo vùng được chạm |
| **Space** | Toggle ghi âm bật/tắt |
| **Ctrl+Shift+Space** | Ẩn / hiện avatar |
| **Ctrl+Shift+H** | Ẩn / hiện chat console |
| **Ctrl+Shift+S** | Chụp màn hình + hỏi AI |
| **Kéo avatar** | Di chuyển trên màn hình |
| **Double click** | Toggle console log |
| **Chuột phải tray** | Settings / Hide / Quit |

### Chat commands

| Lệnh | Tác dụng |
|---|---|
| `/model ollama` | Chuyển sang Ollama local |
| `/model gemini` | Chuyển sang Gemini API |
| `/model openai` | Chuyển sang OpenAI |
| `/model deepseek` | Chuyển sang DeepSeek |
| `/model glm` | Chuyển sang Zhipu GLM |
| `/model qwen` | Chuyển sang DashScope Qwen |
| `/model openai-compatible` | Chuyển sang Custom API |
| `/stt tiny` | Đổi Whisper model (tiny / base / small) |
| `/stt funasr` | Đổi sang FunASR |
| `/sit` | Avatar ngồi xuống |
| `/stand` | Avatar đứng lên |
| `/mic` | Toggle mic prop |

### Chế độ tương tác

**Streamer mode** — mic luôn bật, loop voice liên tục như VTuber thật (mặc định).

**Assistant mode** — chat box hiện, nói chuyện khi hỏi:
```json
"app": { "interactionMode": "assistant" }
```

---

## Cấu hình đầy đủ

`config/companion.config.json`:

```json
{
  "app": {
    "avatarModel": "assets/live2d/IceGirl/IceGirl.model3.json",
    "interactionMode": "streamer"
  },
  "llm": {
    "provider": "ollama",
    "model": "qwen2.5:1.5b",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    "glm_api_key": "",
    "glm_model": "glm-4",
    "qwen_api_key": "",
    "qwen_model": "qwen-plus",
    "openai_compatible_base_url": "",
    "openai_compatible_api_key": "",
    "openai_compatible_model": ""
  },
  "stt": {
    "model": "tiny",
    "language": "vi",
    "funasr_model": "iic/SenseVoiceSmall"
  },
  "tts": {
    "backend": "kokoro",
    "fish_audio_api_key": "",
    "fish_audio_model_id": "",
    "voice": "vi-VN-HoaiMyNeural",
    "gpt_sovits_api_url": "http://127.0.0.1:9880/tts"
  },
  "features": {
    "voice": true,
    "memory": true,
    "documentRag": true,
    "desktopControl": true,
    "screenAwareness": false,
    "twitchMode": false
  },
  "twitch": { "channel": "" }
}
```

Tất cả config có thể chỉnh trong **Settings window** (tray → Settings) mà không cần restart.

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
│   ├── settings.html              # Settings UI đầy đủ với sidebar navigation
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
│   │   ├── event_bus.py           # In-process pub/sub
│   │   └── ui_tars/               # UI-TARS action parser
│   ├── agents/                    # PlannerAgent, MemoryAgent, VisionAgent, DesktopAgent
│   ├── services/
│   │   ├── llm_service.py         # 7 LLM provider + Agent Loop + Tool Calling
│   │   ├── tts_service.py         # Fish Audio / GPT-SoVITS / Kokoro / edge-tts / pyttsx3
│   │   ├── stt_service.py         # faster-whisper / FunASR
│   │   └── memory_service.py      # Short-term + Long-term + relationship + mood
│   ├── persona/                   # system_prompt.py + 4 character YAML files
│   ├── memory/                    # ChromaDB vector store, embeddings, short/long term
│   ├── rag/                       # PDF/DOCX/TXT loader, chunker, retriever
│   ├── tools/                     # computer_control, file_reader, file_writer, browser, screen
│   └── utils/                     # approval_registry, audio_utils, emotion_detector
├── assets/
│   └── live2d/
│       ├── IceGirl/               # + expressions (18 exp), motions, textures
│       ├── hiyori_en/             # 10 motions
│       ├── mao_en/                # 8 expressions, 7 motions
│       └── huohuo2/               # 5 expressions, 5 motions
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
→ Gõ `/stt base` hoặc `/stt small`, hoặc thử `/stt funasr` để dùng FunASR.

**Fish Audio không có tiếng**
→ Kiểm tra API key và Model ID trong Settings. App tự fallback về edge-tts nếu lỗi.

**FunASR lần đầu chậm**
→ Đang tải model từ ModelScope (~500MB). Những lần sau đã cache.

**Kokoro TTS không phát được**
→ Chạy `pip install kokoro soundfile` rồi restart app.

---

## Roadmap

- [x] Avatar Live2D với biểu cảm + lipsync realtime
- [x] Voice conversation — WAV PCM16 → STT → LLM → TTS per-sentence
- [x] VAD + Barge-in + ASR streaming draft
- [x] Fish Audio · GPT-SoVITS · Kokoro offline · edge-tts
- [x] FunASR STT (Alibaba SenseVoice)
- [x] Cognitive loop 4 tầng — Perception → Memory → Emotion → Cognition
- [x] Emotion pipeline — LLM nhúng tag → Live2D expression realtime
- [x] 4 nhân vật + accessory system per-model
- [x] Memory đầy đủ — short-term + long-term ChromaDB + write-back
- [x] Relationship system + Mood drift
- [x] Agent loop + Tool calling native (7 LLM provider)
- [x] Approval flow cho hành động nguy hiểm
- [x] Autonomous loop — tự nói, tự nhận xét màn hình
- [x] Twitch mode — đọc chat, tự comment viewer
- [x] RAG tài liệu (PDF, DOCX, TXT)
- [x] Desktop control + Screen awareness (OCR)
- [x] Settings UI đầy đủ với sidebar navigation, dynamic config per provider
- [ ] Packaging Windows (.exe) với electron-builder
- [ ] Memory UI — xem, sửa, xóa ký ức trong app

---

## Credits

- [Live2D Cubism SDK](https://www.live2d.com/en/sdk/about/) — avatar rendering
- [Open-LLM-VTuber](https://github.com/t41372/Open-LLM-VTuber) — tham khảo WAV recorder và TTS pipeline
- [Fish Audio](https://fish.audio) — voice cloning API
- [Kokoro TTS](https://github.com/hexgrad/kokoro) — offline neural TTS
- [FunASR / SenseVoice](https://github.com/modelscope/FunASR) — streaming ASR
- [Ollama](https://ollama.com) — local LLM runtime
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — STT
- [edge-tts](https://github.com/rany2/edge-tts) — TTS fallback
- [ChromaDB](https://www.trychroma.com) — vector store cho long-term memory

---

<div align="center">
<sub>Dự án cá nhân · Không có cộng đồng hay support chính thức</sub>
</div>