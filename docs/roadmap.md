# Roadmap

## Phase 0 - Project foundation

- Viet tai lieu kien truc, API va module boundary.
- Tao config mac dinh cho companion, persona va hotkey.
- Chuan hoa message contract giua Electron va Python.
- Tao logging va error format thong nhat.

## Phase 1 - Desktop shell

- Khoi dong Electron app.
- Tao tray icon va settings window.
- Tao overlay window always-on-top cho avatar.
- Load Live2D IceGirl trong renderer.
- Ho tro idle, blink, smile va mot vai motion co ban.

## Phase 2 - Local Python service

- Khoi dong FastAPI/WebSocket server.
- Electron connect duoc toi Python service.
- Hoan thien `/health`, `/chat` va WebSocket `user.message`.
- Tao `PlannerAgent` toi thieu de tra loi text.

## Phase 3 - Text chat brain

- Tich hop LLM provider.
- Them persona system prompt.
- Them emotion output va avatar cues.
- UI chat hien thi history va streaming response neu co.

## Phase 4 - Voice conversation

- Microphone capture trong renderer.
- STT pipeline.
- TTS pipeline.
- Audio playback.
- Lipsync co ban dua tren audio amplitude hoac phoneme data.

## Phase 5 - Memory

- Short-term conversation memory.
- User profile memory.
- Long-term semantic memory voi vector store.
- UI cho xem/sua/xoa memory.
- MemoryAgent quyet dinh noi dung can luu.

## Phase 6 - Desktop control

- Mo app theo ten.
- Tim file.
- Doc clipboard.
- Doc file text.
- Confirmation flow cho thao tac rui ro.
- Audit log cho desktop actions.

## Phase 7 - Document RAG

- PDF loader.
- DOCX loader.
- TXT loader.
- Chunking va embedding.
- Retriever theo document/collection.
- Chat voi tai lieu.

## Phase 8 - Screen awareness

- Screenshot request tu Electron.
- OCR.
- VisionAgent mo ta noi dung man hinh.
- Hoi-dap ve loi dang hien thi.
- Che do screen-aware co toggle rieng.

## Phase 9 - Polish

- Settings day du cho voice, model, memory, avatar.
- Hotkeys: push-to-talk, hide/show avatar, screen ask.
- Startup behavior.
- Packaging cho Windows.
- Crash recovery va offline fallback.
