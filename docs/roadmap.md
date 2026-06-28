# Lộ trình Phát triển (Roadmap)

Lộ trình phát triển hệ thống trợ lý ảo AI Companion DeskAgent.

---

## 🟢 Phase A — Nền tảng Ổn định & Đồng hành (Đã Hoàn thành)

Mục tiêu: Đưa ứng dụng vào hoạt động ổn định, chat được, avatar hiển thị mượt mà, bộ nhớ lưu trữ thông minh và hoạt động tự trị.

- **Sửa lỗi khởi động (Startup Flow)**: Chạy song song Electron và Backend Python không lỗi ngầm.
- **Tách cấu trúc LLM Providers**: Tách monolithic LLM gateway thành các provider adapters độc lập (`GeminiProvider`, `OpenAIProvider`, `OllamaProvider`).
- **Phân tách bộ nhớ (Decoupled Memory)**: Chuyển dữ liệu bộ nhớ dài hạn sang ChromaDB Memory Store nằm ngoài RAG.
- **Tích hợp cảm xúc tự trị (Autonomous Life Loop)**: Kết nối `feel_engine` và `reflect_engine` vào vòng lặp tự trị để nhân vật tự động cập nhật tâm trạng và suy nghĩ.
- **Định dạng ContextPacket**: Định nghĩa dữ liệu truyền nhận dạng Dataclass `ContextPacket` kết hợp tính năng tương thích ngược dạng Dictionary.
- **Tích hợp Luồng đồng cảm & Động lực**:
    - Sử dụng `EmpathyEngine` để phân tích cảm xúc từ tin nhắn người dùng và đề xuất tông giọng (`recommended_tone`).
    - Gọi `MotivationManager` cập nhật wellbeing, boredom, curiosity và inject trực tiếp vào prompt hệ thống.
- **Kết nối Luồng học tập**: Kích hoạt `self_reflection`, `learning_manager` và `experience_store` sau khi hoàn thành hoặc thất bại các kế hoạch (Plan).
- **Kiểm thử di động (Portable Integration Tests)**: Chuyển toàn bộ đường dẫn tĩnh sang định vị tương đối để chạy được trên bất kỳ môi trường CI/CD nào.

---

## 🟡 Phase B — Tương tác Thời gian thực & Tri thức Ngữ nghĩa (Hiện tại)

Mục tiêu: Tối ưu hóa độ trễ phản hồi giọng nói và bắt đầu hệ thống hóa hiểu biết của trợ lý ảo về người dùng.

- **Truyền dẫn mã nguồn Token (LLM Token Streaming)**:
    - Triển khai `StreamHandler` gom nhóm token LLM và chia nhỏ thành các câu hoàn chỉnh dựa trên dấu câu nhằm giảm độ trễ TTS.
- **Nhận dạng giọng nói trực tiếp (Streaming STT)**:
    - Hiện thực hóa `StreamSTT` quản lý ghi nhận PCM audio chunk và cập nhật văn bản tức thời qua callbacks.
- **Đồ thị tri thức (Knowledge Graph)**:
    - Phát triển mạng lưới `KnowledgeGraph` lưu trữ mối quan hệ Triplet (Entity-Relation).
    - Tạo `GraphBuilder` phân tích thông tin từ văn bản để phát hiện và nạp tự động các bộ ba ngữ nghĩa.
- **Lớp tri thức ngữ nghĩa (Ontology)**:
    - Triển khai `Ontology` để quản lý các quan hệ thừa kế phân loại khái niệm (ví dụ: `vscode IS_A editor`).
- **Đồng bộ hóa Vision Service**:
    - Chuyển giao toàn bộ vai trò chụp màn hình và mô tả GUI cho `VisionAgent` để hợp nhất xử lý đa phương thức (multimodal).

---

## 🔴 Phase C — Tự trị Nâng cao & Đóng gói Phân phối (Kế tiếp)

Mục tiêu: Tối ưu hóa hiệu năng, đóng gói phát hành và cho phép hoạt động đa tác vụ độc lập.

- **Đóng gói sản phẩm (Production Packaging)**:
    - Cấu hình PyInstaller cho Backend Python và Electron Builder cho Frontend Desktop thành tệp cài đặt `.exe` duy nhất.
- **Cơ chế ngắt giọng nói nâng cao (Voice Interruption)**:
    - Tối ưu hóa cờ hiệu hủy tiến trình trong `InterruptionHandler` để dừng phát âm thanh ngay lập tức khi phát hiện người dùng nói xen vào.
- **Hoàn thiện các lớp học tập nâng cao**:
    - Triển khai Habit Tracker đúc kết thói quen người dùng theo chu kỳ tuần/tháng.
