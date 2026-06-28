# Tài liệu Kiến trúc Hệ thống (DeskAgent v7/v8)

## 1. Tầm nhìn Sản phẩm

AI Companion DeskAgent là trợ lý cá nhân dạng nhân vật ảo 2D/2.5D tương tác trực tiếp ngay trên màn hình nền (Desktop) hệ điều hành Windows. 

Điểm nhấn trải nghiệm cốt lõi:
- **Tính cá nhân sinh động**: Nhân vật có cảm xúc tự trị (`life_loop`), biết vui buồn giận dỗi dựa vào hoạt động, thói quen của người dùng và thời gian trong ngày.
- **Khả năng đồng cảm (Empathy)**: Nhận thức cảm xúc của người dùng từ văn bản để thay đổi tông giọng và thái độ phản hồi.
- **Tri thức ngữ nghĩa & Học tập**: Tích lũy bộ nhớ dài hạn, tự động ghi nhớ sở thích vào đồ thị tri thức (`KnowledgeGraph`) và tự rút bài học kinh nghiệm (`self_reflection`).
- **Computer Use & Vision**: Hỗ trợ nhìn màn hình (screenshot/OCR/VLM) và trực tiếp điều khiển chuột, bàn phím, chạy lệnh hệ thống có kiểm soát an toàn.

---

## 2. Kiến trúc Tổng thể (Flat Hybrid Node/Python Workspace)

DeskAgent được tổ chức theo cấu trúc phẳng kết hợp giữa Electron (Frontend UI) và Python (Backend AI Runtime) nhằm tối ưu hóa hiệu năng và đơn giản hóa việc import module:

```text
                               +-----------------------------------+
                               |       Màn hình người dùng         |
                               +-----------------+-----------------+
                                                 |
                                                 | (Chuột/Bàn phím/Microphone)
                                                 v
+----------------------------------------------------------------------------------+
|                              Electron UI Desktop                                 |
|                                                                                  |
|  +------------------------+  +--------------------------+  +------------------+  |
|  | desktop/ (Main Process)|  | renderer/ (UI Rendering) |  | src/ (TypeScript)|  |
|  +------------------------+  +--------------------------+  +------------------+  |
+----------------------------------------+-----------------------------------------+
                                         |
                                         | (WebSocket / Local HTTP APIs)
                                         v
+----------------------------------------------------------------------------------+
|                            Python AI Backend Engine                              |
|                                                                                  |
|  +-----------------------+  +-------------------------+  +--------------------+  |
|  |   api/ (server.py)    |  |  cognition/ (Bộ não AI) |  |   life/ (LifeLoop) |  |
|  +-----------------------+  +-------------------------+  +--------------------+  |
|  |   memory/ (ChromaDB)  |  |  motivation/ (Động lực) |  |   social/ (Empathy)|  |
|  +-----------------------+  +-------------------------+  +--------------------+  |
|  |  execution/ (Executor)|  |  tools/ (pyautogui wrapper)|  |   vision/ (OCR/VLM)|  |
|  +-----------------------+  +-------------------------+  +--------------------+  |
+----------------------------------------------------------------------------------+
```

---

## 3. Các Phân lớp Chức năng chính

### 3.1 Electron Frontend UI
*   `desktop/`: Quản lý vòng đời ứng dụng Electron, hiển thị nhan vật overlay trong suốt, tray icon, cấu hình hotkey toàn cục, truyền thông IPC và vận hành WebSocket client kết nối đến Backend Python.
*   `renderer/`: Trực quan hoá mô hình Live2D/Spine, thực hiện Lipsync miệng nhân vật đồng bộ với biên độ âm thanh TTS, và điều phối microphone thu âm giọng nói.
*   `src/`: Chứa mã nguồn TypeScript hỗ trợ nghiệp vụ chung và các cấu trúc cấu hình dùng chung ở Frontend.

### 3.2 Python Backend Services
*   **API Gateway (`api/server.py`)**: Máy chủ FastAPI/WebSocket đóng vai trò trung chuyển thông điệp thời gian thực, quản lý phân phối luồng phản hồi LLM cùng chỉ thị chuyển động/cảm xúc của avatar.
*   **Bộ não nhận thức (`cognition/`)**:
    *   `CognitionEngine`: Điều phối luồng làm việc 5 bước (Recall memory $\rightarrow$ Analyze Empathy $\rightarrow$ Update motivation/state $\rightarrow$ Call LLM stream $\rightarrow$ Writeback memory).
    *   `ContextManager`: Lưu trữ lịch sử `ContextPacket` làm cơ sở suy luận.
    *   `PromptLibrary`: Lưu trữ các mẫu chỉ thị hệ thống.
*   **Hệ thống Động lực & Tự trị (`motivation/`, `life/`)**:
    *   `MotivationManager`: Tick nhịp sinh học mỗi 30 giây để cập nhật Wellbeing, Boredom, Curiosity và Intrinsic Drives.
    *   `LifeLoop`: Vòng lặp autonomously observe $\rightarrow$ feel $\rightarrow$ think $\rightarrow$ decide $\rightarrow$ act $\rightarrow$ reflect.
*   **Mạng lưới Xã hội (`social/`)**:
    *   `EmpathyEngine`: Nhận diện cảm xúc người dùng (happy, sad, frustrated...) để hướng dẫn mô hình trả lời theo tông giọng khuyến nghị.
    *   `RelationshipTracker`: Đo lường điểm thân thiết để thay đổi cách xưng hô của IceGirl.
*   **Tầng Lưu trữ (`memory/`)**:
    *   `MemoryManager`: Đầu mối duy nhất phân giải thông tin từ bộ nhớ ngắn hạn, dài hạn và các tệp văn bản.
    *   `ChromaMemoryStore`: Database vector lưu facts dài hạn, tách biệt hoàn toàn khỏi RAG tài liệu thông thường.
*   **Tầng Thực thi & Thị giác (`execution/`, `tools/`, `vision/`)**:
    *   `MouseController`, `KeyboardController`: Kiểm duyệt toạ độ an toàn trước khi bấm chuột/gõ phím.
    *   `TerminalExecutor`: Thực thi các lệnh console và kiểm tra phê duyệt an toàn từ người dùng qua PermissionManager (Human-in-the-loop).
    *   `VisionService` / `VisionAgent`: Chụp ảnh màn hình, chạy OCR (pytesseract) hoặc VLM (Gemini/OpenAI) để xác định toạ độ nút bấm dựa trên mô tả.

---

## 4. Nguyên tắc Thiết kế Code

1.  **Safety First (An toàn là trên hết)**: Mọi thao tác ghi/xóa file ngoài thư mục dự án hoặc chạy lệnh command line bắt buộc phải thông qua `PermissionManager` và đợi phê duyệt trực tiếp của người dùng.
2.  **Modular & Decoupled (Tách biệt module)**: Electron chỉ xử lý giao diện hiển thị; Python Service chỉ xử lý tính toán AI. Hai bên giao tiếp qua hợp đồng API chuẩn.
3.  **Low Latency (Trễ tối thiểu)**: Sử dụng luồng streaming từ token LLM $\rightarrow$ StreamHandler gom câu $\rightarrow$ TTS chunking để đảm bảo nhân vật phản hồi giọng nói tức thời trong vòng dưới 1.5 giây.
