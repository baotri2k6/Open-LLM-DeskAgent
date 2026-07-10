# Thiết kế API Nội bộ

Tài liệu mô tả giao thức truyền thông HTTP và WebSocket giữa ứng dụng Desktop (Electron) và Backend AI Python (FastAPI/WebSocket). Địa chỉ kết nối mặc định của service: `http://127.0.0.1:8765`.

---

## 1. WebSocket Giao tiếp Thời gian thực

Đường dẫn kết nối:
```text
ws://127.0.0.1:8765/ws
```

Dùng cho việc gửi nhận tin nhắn thời gian thực, audio streaming, trạng thái của robot/avatar (emotion/motion) và cập nhật tiến trình chạy tool.

### 1.1 Client -> Server (Gửi lên từ Electron)

#### Tin nhắn người dùng (`user.message`)
```json
{
  "id": "msg_uuid_123",
  "type": "user.message",
  "inputMode": "text",
  "text": "Mở VS Code giúp tôi",
  "attachments": [],
  "context": {
    "locale": "vi-VN",
    "activeWindow": "Desktop"
  }
}
```

#### Tiến trình âm thanh giọng nói (`voice.transcript`)
```json
{
  "id": "voice_uuid_456",
  "type": "voice.transcript",
  "text": "Bây giờ là mấy giờ rồi?",
  "isFinal": true
}
```

---

### 1.2 Server -> Client (Trả về từ Python Service)

#### Phản hồi của trợ lý ảo (`assistant.response`)
```json
{
  "id": "res_uuid_789",
  "type": "assistant.response",
  "text": "Mình đang mở VS Code cho bạn nhé.",
  "emotion": "smile",
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

#### Phân đoạn âm thanh TTS phát đi (`assistant.speech`)
```json
{
  "id": "speech_uuid_999",
  "type": "assistant.speech",
  "text": "Bây giờ là 3 giờ chiều rồi.",
  "audioUrl": "cache/tts/speech_999.wav",
  "durationMs": 1800
}
```

---

## 2. Các Endpoint HTTP RESTful

### GET `/health`
Kiểm tra trạng thái sẵn sàng của backend và các mô hình AI.
*   **Response**:
    ```json
    {
      "status": "ok",
      "version": "0.7.0",
      "subsystems": {
        "llm": "connected",
        "vectorstore": "ready",
        "stt": "ready",
        "tts": "ready"
      }
    }
    ```

### GET `/api/companion/state`
Truy vấn trạng thái thời gian thực của IceGirl (cảm xúc ngắn hạn, tâm trạng dài hạn, quan hệ thân mật, mục tiêu ngày và trạng thái động lực).
*   **Response**:
    ```json
    {
      "emotion": {
        "current": "smile",
        "intensity": 0.8
      },
      "mood": {
        "mood": "vui vẻ",
        "energy": 0.75,
        "stress": 0.15
      },
      "relationship": {
        "level": "Bạn thân",
        "score": 120
      },
      "goals": {
        "today_goal": "Hỗ trợ học Python",
        "progress": "50%"
      },
      "motivation": {
        "wellbeing": 0.9,
        "boredom": {
          "level": 0.1,
          "label": "engaged"
        },
        "curiosity": {
          "top_interests": ["cờ vua", "programming"]
        }
      }
    }
    ```

### POST `/chat`
Gửi tin nhắn văn bản đơn giản đồng bộ không streaming.
*   **Request**:
    ```json
    {
      "text": "Tóm tắt file report này",
      "context": {
        "documentId": "doc_xyz"
      }
    }
    ```

### POST `/documents/import`
Nạp tài liệu (PDF, DOCX, TXT) vào RAG vector store.
*   **Request**:
    ```json
    {
      "path": "D:/Documents/report.pdf",
      "collection": "default"
    }
    ```
