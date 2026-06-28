# AI Companion Desktop 2D - Architecture

## 1. Tam nhin san pham

AI Companion Desktop 2.5D la tro ly AI dang nhan vat ao song tren man hinh Windows. Ung dung ket hop:

- Nhan vat 2.5D co bieu cam, chuyen dong va lipsync.
- Tro chuyen bang giong noi theo thoi gian gan thuc.
- Dieu khien may tinh theo lenh nguoi dung.
- Doc tai lieu va tra loi dua tren noi dung rieng cua nguoi dung.
- Tri nho dai han ve nguoi dung, du an va so thich.
- Kha nang nhin man hinh bang screenshot, OCR va vision model.

Muc tieu trai nghiem: nguoi dung co cam giac dang noi voi mot nhan vat that tren desktop, khong phai chi mot chatbot trong cua so.

## 2. Kien truc tong the

```text
User
  |
  | voice / text / hotkey / screen command
  v
Electron Desktop App
  |
  | WebSocket / HTTP
  v
Python AI Services
  |
  +-- Agent Layer
  |     +-- PlannerAgent
  |     +-- MemoryAgent
  |     +-- VisionAgent
  |     +-- DesktopAgent
  |     +-- BrowserAgent
  |
  +-- Service Layer
  |     +-- LLMService
  |     +-- STTService
  |     +-- TTSService
  |     +-- MemoryService
  |     +-- VisionService
  |     +-- SystemService
  |
  +-- Tool Layer
  |     +-- open_app
  |     +-- file_reader
  |     +-- screen_reader
  |     +-- clipboard_tool
  |     +-- browser_control
  |     +-- web_search
  |
  +-- Data Layer
        +-- short-term memory
        +-- long-term memory
        +-- vector store
        +-- user profile
        +-- config
```

Electron phu trach desktop UX, avatar va giao tiep voi he dieu hanh o muc UI. Python phu trach AI, agent orchestration, memory, document understanding, vision va tool execution.

## 3. Frontend Desktop Layer

### Electron main process

Thu muc: `electron/`

Vai tro:

- Tao cua so chat, overlay avatar va settings.
- Quan ly tray icon, hotkey, window positioning.
- Lam cau noi IPC giua renderer va Python services.
- Kiem soat quyen thao tac desktop nhay cam.

Module de xuat:

- `electron/main.js`: diem khoi dong ung dung.
- `electron/preload.js`: expose API an toan cho renderer.
- `electron/ipc/ai.ipc.js`: gui message toi Python AI service.
- `electron/ipc/voice.ipc.js`: voice input/output events.
- `electron/ipc/system.ipc.js`: lenh he thong nhu mo app, chup man hinh.
- `electron/ipc/avatar.ipc.js`: bieu cam, motion, lipsync.
- `electron/window/overlay.js`: cua so nhan vat trong suot, always-on-top.
- `electron/window/settings.js`: cau hinh model, voice, hotkey, memory.
- `electron/window/tray.js`: menu system tray.

### Renderer

Thu muc: `renderer/`

Vai tro:

- Hien thi avatar 2.5D.
- Hien thi chat transcript.
- Ghi am microphone va phat TTS audio.
- Gui event UI ve Electron main process.

Module de xuat:

- `renderer/index.html`: man hinh chinh gom avatar va chat surface.
- `renderer/settings.html`: trang cau hinh.
- `renderer/scripts/avatar/live2d-manager.js`: load model Live2D.
- `renderer/scripts/avatar/expression.js`: map emotion sang expression.
- `renderer/scripts/avatar/motion.js`: idle, blink, head tilt, surprise.
- `renderer/scripts/avatar/lipsync.js`: dong bo am thanh voi mieng nhan vat.
- `renderer/scripts/voice/mic-listener.js`: microphone capture.
- `renderer/scripts/voice/audio-player.js`: phat TTS va emit lipsync data.
- `renderer/scripts/chat/chat-ui.js`: UI chat.
- `renderer/scripts/chat/history.js`: lich su hoi thoai ngan han tren UI.

## 4. Python AI Services

Thu muc: `python-services/`

Python service chay nhu backend local. Electron ket noi bang WebSocket cho event realtime va HTTP cho tac vu request/response.

### Core

- `main_server.py`: khoi dong FastAPI/WebSocket server.
- `core/message_router.py`: nhan message tu Electron, chon pipeline xu ly.
- `core/websocket_manager.py`: quan ly client Electron.
- `core/event_bus.py`: pub/sub noi bo giua service va agent.
- `core/config.py`: doc config tu `config/*.json` va `.env`.
- `core/logger.py`: logging co cau truc.

### Services

- `services/stt_service.py`: speech-to-text.
- `services/tts_service.py`: text-to-speech.
- `services/llm_service.py`: goi model ngon ngu.
- `services/memory_service.py`: doc/ghi tri nho.
- `services/vision_service.py`: OCR, screenshot understanding, image QA.
- `services/system_service.py`: thao tac OS duoc cho phep.

### Agents

- `PlannerAgent`: bo nao dieu phoi. Nhan y dinh nguoi dung, tach task, chon agent/tool.
- `MemoryAgent`: quyet dinh cai gi can nho, truy hoi ky uc lien quan.
- `VisionAgent`: hieu screenshot, OCR, loi tren man hinh, hinh anh.
- `DesktopAgent`: mo app, tim file, doc clipboard, thao tac desktop.
- `BrowserAgent`: thao tac browser, tim kiem web neu duoc phep.

Agent khong nen goi truc tiep UI. Agent tra ve `AssistantResponse` co text, emotion, action, memory updates va avatar cues. Renderer se bien cac cue nay thanh bieu cam/chuyen dong.

## 5. Luong xu ly chinh

### 5.1 Tro chuyen bang giong noi

```text
Microphone
  -> STTService
  -> MessageRouter
  -> PlannerAgent
  -> MemoryAgent retrieves context
  -> LLMService generates answer
  -> MemoryAgent stores useful facts
  -> TTSService generates audio
  -> Electron emits avatar expression + lipsync
  -> User hears voice and sees character react
```

Ket qua tra ve frontend nen co dang:

```json
{
  "type": "assistant.response",
  "text": "Hien tai la 3 gio chieu.",
  "emotion": "friendly",
  "speechAudioUrl": "cache/tts/response.wav",
  "avatar": {
    "expression": "smile",
    "motion": "nod",
    "lipsync": true
  }
}
```

### 5.2 Lenh dieu khien may tinh

Vi du: "Mo VS Code"

```text
User request
  -> PlannerAgent detects desktop action
  -> DesktopAgent validates action
  -> SystemService executes open_app
  -> Assistant explains result
```

Nhung thao tac rui ro nhu xoa file, gui email, cai dat phan mem, chay lenh terminal nen can confirm truoc.

### 5.3 Doc tai lieu rieng

```text
User imports PDF/DOCX/PPTX/TXT
  -> loader extracts text
  -> chunker splits content
  -> embeddings creates vectors
  -> vector store saves chunks
  -> user asks question
  -> retriever finds relevant chunks
  -> LLM answers with document context
```

Thu muc lien quan:

- `python-services/rag/pdf_loader.py`
- `python-services/rag/docx_loader.py`
- `python-services/rag/txt_loader.py`
- `python-services/rag/chunker.py`
- `python-services/rag/retriever.py`

### 5.4 Tri nho dai han

Memory chia thanh 3 lop:

- Short-term: noi dung hoi thoai hien tai.
- Long-term profile: ten, so thich, muc tieu, du an dang lam.
- Semantic memory: cac su kien/ghi chu duoc embedding de truy hoi.

Quy tac:

- Khong ghi tat ca message vao long-term memory.
- Chi ghi thong tin ben vung, huu ich, duoc suy ra ro rang.
- Cho nguoi dung xem, sua, xoa tri nho.

### 5.5 Nhin man hinh

```text
User: "Loi nay sua sao?"
  -> Electron captures screenshot
  -> VisionService runs OCR + visual model
  -> VisionAgent summarizes visible problem
  -> PlannerAgent asks LLM for fix
  -> Assistant answers with steps
```

Nen tach screenshot thanh action co quyen rieng. Mac dinh chi chup khi nguoi dung yeu cau hoac bat che do "screen aware".

## 6. Hop dong message noi bo

### UserMessage

```json
{
  "id": "msg_001",
  "type": "user.message",
  "inputMode": "voice",
  "text": "Mo VS Code giup toi",
  "attachments": [],
  "context": {
    "activeWindow": "Desktop",
    "locale": "vi-VN"
  }
}
```

### AssistantResponse

```json
{
  "id": "res_001",
  "type": "assistant.response",
  "text": "Minh dang mo VS Code.",
  "emotion": "helpful",
  "actions": [
    {
      "type": "desktop.open_app",
      "status": "completed",
      "target": "Visual Studio Code"
    }
  ],
  "avatar": {
    "expression": "smile",
    "motion": "nod",
    "lipsync": true
  },
  "memory": {
    "stored": []
  }
}
```

### ToolCall

```json
{
  "id": "tool_001",
  "type": "tool.call",
  "tool": "open_app",
  "args": {
    "name": "Visual Studio Code"
  },
  "requiresConfirmation": false
}
```

## 7. Emotion va Avatar Mapping

LLM/Agent chi nen tra ve emotion o muc semantic. Renderer moi quyet dinh asset Live2D nao duoc dung.

Bang mapping de xuat:

| Emotion   | Expression | Motion    | Use case                   |
| --------- | ---------- | --------- | -------------------------- |
| neutral   | normal     | idle      | Tra loi thong thuong       |
| friendly  | smile      | nod       | Chao hoi, xac nhan         |
| thinking  | focused    | look_side | Dang suy nghi              |
| surprised | surprised  | head_back | Gap loi, thong tin bat ngo |
| sad       | sad        | look_down | Dong cam, that bai         |
| excited   | happy      | bounce    | Thanh cong, khen ngoi      |

## 8. Bao mat va quyen rieng tu

Day la ung dung desktop co quyen nhay cam, nen can thiet ke theo mac dinh an toan:

- Voice recording chi bat khi wake word, push-to-talk hoac nut mic duoc kich hoat.
- Screenshot chi chup khi co lenh ro rang hoac che do screen-aware duoc bat.
- Desktop actions can confirm voi lenh rui ro.
- Memory co giao dien xem/sua/xoa.
- Log khong ghi API key, token, noi dung tai lieu nhay cam neu khong can.
- Tool execution can danh sach cho phep, khong cho agent chay lenh tuy y.

## 9. Cau truc thu muc de xuat

```text
AI_Companion/
  assets/
    live2d/
    sounds/
  config/
    companion.config.json
    hotkeys.config.json
    persona.config.json
  data/
    user_profile.json
  docs/
    architecture.md
    api.md
    roadmap.md
  electron/
    ipc/
    window/
    main.js
    preload.js
  renderer/
    scripts/
      avatar/
      chat/
      voice/
    styles/
    index.html
    settings.html
  python-services/
    agents/
    core/
    memory/
    persona/
    rag/
    services/
    tools/
    utils/
    main_server.py
  tests/
```

## 10. Nguyen tac thiet ke code

- Electron khong chua logic AI phuc tap.
- Python service khong phu thuoc vao UI cu the.
- Agents ra quyet dinh, Services lam viec voi model/API, Tools thuc hien thao tac cu the.
- Moi tool desktop phai co input/output ro rang va co kha nang validate.
- Moi response nen co text + emotion + avatar cue.
- Memory la tinh nang rieng, khong tron lan vao LLM prompt builder.
- RAG pipeline tach loader, chunker, embedding, retriever.
- Uu tien chay local neu co the, nhung cho phep thay provider STT/TTS/LLM.
