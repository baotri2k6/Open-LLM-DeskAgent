# Local API Design

API noi bo giua Electron va Python AI service. Mac dinh service chay local, vi du `http://127.0.0.1:8765`.

## WebSocket

Endpoint:

```text
ws://127.0.0.1:8765/ws
```

Dung cho chat realtime, voice events, avatar cues va tool progress.

### Client -> Server

#### user.message

```json
{
  "id": "msg_001",
  "type": "user.message",
  "inputMode": "text",
  "text": "Mo VS Code",
  "attachments": [],
  "context": {
    "locale": "vi-VN",
    "activeWindow": "Desktop"
  }
}
```

#### voice.transcript

```json
{
  "id": "voice_001",
  "type": "voice.transcript",
  "text": "May gio roi?",
  "isFinal": true
}
```

#### screen.capture.request

```json
{
  "id": "screen_001",
  "type": "screen.capture.request",
  "reason": "user_asked_screen_question"
}
```

### Server -> Client

#### assistant.response

```json
{
  "id": "res_001",
  "type": "assistant.response",
  "text": "Minh da mo VS Code.",
  "emotion": "friendly",
  "avatar": {
    "expression": "smile",
    "motion": "nod",
    "lipsync": true
  },
  "actions": [
    {
      "type": "desktop.open_app",
      "status": "completed",
      "target": "Visual Studio Code"
    }
  ]
}
```

#### assistant.speech

```json
{
  "id": "speech_001",
  "type": "assistant.speech",
  "text": "Hien tai la 3 gio chieu.",
  "audioUrl": "cache/tts/speech_001.wav",
  "durationMs": 1800
}
```

#### tool.progress

```json
{
  "id": "tool_001",
  "type": "tool.progress",
  "tool": "file_reader",
  "status": "running",
  "message": "Dang doc tai lieu..."
}
```

#### confirmation.request

```json
{
  "id": "confirm_001",
  "type": "confirmation.request",
  "title": "Xac nhan thao tac",
  "message": "Ban co muon AI mo file nay khong?",
  "action": {
    "type": "desktop.open_file",
    "target": "D:/Documents/report.docx"
  }
}
```

## HTTP

HTTP dung cho tac vu khong can streaming.

### GET /health

Tra ve trang thai service.

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

### POST /chat

Gui message text don gian.

```json
{
  "text": "Tom tat chuong 3",
  "context": {
    "documentId": "doc_001"
  }
}
```

### POST /documents/import

Import tai lieu vao RAG.

```json
{
  "path": "D:/Documents/book.pdf",
  "collection": "default"
}
```

### GET /memory/profile

Lay user profile va memory tom tat.

### PATCH /memory/profile

Cap nhat thong tin nguoi dung.

```json
{
  "name": "Tri",
  "preferences": {
    "language": "vi-VN"
  }
}
```

## Error format

```json
{
  "type": "error",
  "code": "tool_not_allowed",
  "message": "Thao tac nay can xac nhan cua nguoi dung."
}
```
