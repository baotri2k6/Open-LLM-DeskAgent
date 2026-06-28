<div align="center">

# 🎀 Open LLM DeskAgent (Vision 4.0)

**AI Companion sống động trên Desktop — Độc thoại nội tâm, Tiến hóa cá tính, Điều phối đa tác nhân song song và Tự chủ hoạt động.**

*Lấy cảm hứng từ Neuro-sama. Chạy hoàn toàn cục bộ (offline/local) hoặc qua API đám mây.*

[![Version](https://img.shields.io/badge/version-1.0.0--beta-purple?style=for-the-badge)](https://github.com/baotri2k6/Open-LLM-DeskAgent)
[![License](https://img.shields.io/badge/license-MIT-orange?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=for-the-badge)](#)
[![Python](https://img.shields.io/badge/python-3.10+-yellow?style=for-the-badge)](https://www.python.org)
[![Node](https://img.shields.io/badge/node-18+-green?style=for-the-badge)](https://nodejs.org)

---

**Open LLM DeskAgent** không chỉ đơn thuần là một chatbot hay một widget máy tính vô hồn. Đây là một **AI Companion thực sự sống trên màn hình của bạn** dưới dạng avatar tương tác trực quan (Live2D/Spine). Dự án kết hợp các mô hình ngôn ngữ lớn (LLM), thị giác máy tính (VLM), tổng hợp giọng nói tự nhiên (TTS), và bộ nhớ dài hạn cục bộ để tạo ra một thực thể có cá tính, cảm xúc, có khả năng tự nhận thức màn hình và trực tiếp giúp bạn điều khiển máy tính.

</div>

---

## 🌟 Các Tính Năng Nổi Bật (Cập nhật Vision 4.0)

### 🧠 1. Vòng lặp Độc thoại Nội tâm & Tự trị (Autonomous Life Loop & Thinker)
*   **Life Loop**: Hoạt động theo chu trình tự trị khép kín: *Quan sát (Observe) → Cảm nhận (Feel) → Độc thoại Nội tâm (Think) → Quyết định (Decide) → Hành động (Act)*.
*   **Thinker Engine**: Tầng tư duy độc thoại nội tâm phân tích mức năng lượng của companion, thói quen người dùng và chính sách im lặng để đưa ra ý định phù hợp.
*   **Silence Engine (Chính sách im lặng)**: Companion biết khi nào **không nên nói**. Nếu bạn đang tập trung code hoặc làm việc (`coding`, `terminal_work`), companion sẽ tự động ghi đè ý định và im lặng để tránh làm phiền bạn.
*   **Barge-in (Nói đè)**: Hệ thống VAD (Voice Activity Detection) giám sát thời gian thực. Khi AI đang nói, bạn có thể nói chen vào; AI sẽ lập tức dừng phát âm thanh để lắng nghe bạn.

### 🎭 2. Tiến hóa Cá tính & Mối quan hệ đa chiều (Companion Evolution)
*   **Dynamic Personality**: Tính cách tự động tiến hóa theo thời gian thực. Khi điểm thân thiết đạt mốc **Bạn thân** hoặc **Tri kỷ** (đạt trên 800 điểm), companion sẽ tự động mở khóa các phong cách nói chuyện thân thiết hơn (`casual`, `intimate`, `teasing`).
*   **User Habit Awareness**: Tự động ghi nhận thói quen người dùng (ví dụ: cú đêm `night_owl`, sở thích sử dụng VS Code) để bổ sung vào chủ đề trò chuyện ưa thích.
*   **Định danh nhất quán (Persistent Identity)**: Toàn bộ tiến trình mối quan hệ, các trò đùa riêng (`inside_jokes`), số lượng trải nghiệm chung (`shared_experiences`), cùng toàn bộ cơ sở niềm tin (`BeliefStore`) được tự động lưu bền vững dưới dạng tệp tin JSON (`user_profile.json`, `user_beliefs.json`) để đồng bộ hoàn hảo sau mỗi lần khởi động lại máy.

### 🤖 3. Điều phối Đa tác nhân Song song (Multi-Agent Ecosystem)
*   **AgentCoordinator**: Đóng vai trò orchestrator định tuyến và phân bổ công việc thông minh đến các tác nhân chuyên trách (`planner`, `desktop`, `browser`, `coding`, `vision`, `memory`).
*   **Parallel Execution**: Hỗ trợ khởi chạy đồng thời nhiều subagents thông qua cơ chế bất đồng bộ `asyncio.gather`, gộp kết quả và phản hồi trực tiếp cho người dùng.

### 💻 4. Thao tác Hệ thống & Thị giác Máy tính (Computer Use)
*   **UI-TARS Grounding**: Sử dụng các mô hình thị giác (VLM) để định vị và nhấp chuột vào bất kỳ phần tử nào trên màn hình thông qua tọa độ chuẩn hóa `[0, 1000]`.
*   **Hành động mượt mà**: Di chuyển chuột trượt dần tự nhiên (`pyautogui.moveTo` với duration), tự động chờ trình duyệt tải trang trước khi thao tác tiếp theo.
*   **Hệ thống Phân quyền An toàn**: `PermissionManager` kiểm soát các lệnh nguy hại thông qua cơ chế duyệt trước (như chạy shell script, chỉnh sửa tệp tin hệ thống).
*   **Autonomous SWE-Runner**: Lõi tác nhân kỹ sư phần mềm tự trị (`mini_swe_runner.py`). Agent tự động tìm kiếm file lỗi, viết code sửa đổi, chạy unit tests (`pytest`), và tự sửa lỗi nếu test fail.

### 🎭 5. Hoạt ảnh Tương tác Trực quan (Live2D & Spine)
*   **4 Nhân vật Live2D độc đáo**: *IceGirl* (lém lỉnh, trêu chọc), *Hiyori* (năng động, tươi cười), *Mao* (Tsundere thời trang), và *Huohuo* (phán quan nhút nhát).
*   **WebGL Click-Through**: Khả năng chạm xuyên vật thể thông minh. Hệ thống tự động đọc kênh Alpha của WebGL context tại vị trí con trỏ chuột để bỏ qua (ignore mouse events) khi cursor nằm trên các vùng trong suốt.
*   **Lipsync & Emotion Realtime**: Phân tích tần số âm thanh thời gian thực để tạo khẩu hình nhép miệng (lipsync) khớp với giọng nói. Tự động chuyển đổi biểu cảm khuôn mặt tương ứng với nhãn cảm xúc sinh ra từ LLM.

---

## 📐 Cấu Trúc Dự Án

```text
Open-LLM-DeskAgent/
├── runtime/                 # AI Runtime Kernel (vòng đời, state, scheduler)
├── life/                    # Nhịp sinh hoạt tự trị (Observe→Feel→Think→Decide→Act)
├── perception/              # Thu thập dữ liệu đầu vào (voice, screen, vision)
├── persona/                 # Cá tính, cảm xúc, mối quan hệ & biểu cảm Live2D
├── memory/                  # Hệ thống ký ức (working, episodic, semantic)
├── cognition/               # Lớp suy luận logic & độc thoại nội tâm (Reasoning, reflection)
├── decision/                # Tầng quyết định (silence policy, action selector)
├── belief/                  # Cơ sở niềm tin bền vững (user model, belief store)
├── agents/                  # Các Agent chuyên biệt & Subagent Service
├── execution/               # Thao tác hệ thống (keyboard, mouse, browser, terminal)
├── tools/                   # Công cụ hệ thống cơ bản
├── llm/                     # LLM Gateway (providers, prompts, parser)
├── speech/                  # STT + TTS Pipelines (whisper, funasr, edge, kokoro)
├── vision/                  # Vision Pipeline (ocr, grounding, screen understanding)
├── desktop/                 # Electron Main Process (ipc, windows, tray)
├── renderer/                # Electron Renderer UI (avatar, chat, settings)
├── live2d/                  # Live2D Runtime
├── api/                     # HTTP/WebSocket Server & Telegram Bridge
├── config/                  # Tệp cấu hình hệ thống
├── database/                # SQLite, VectorDB layers
├── assets/                  # Live2D models, icons, images
├── scripts/                 # Build & start scripts
└── tests/                   # Kịch bản kiểm thử tích hợp (Phases 2-9)
```

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

### Yêu Cầu Hệ Thống
*   **Hệ điều hành**: Windows 10/11 (Hoặc Linux/macOS cho chế độ phát triển).
*   **Phần mềm cài sẵn**: Python 3.10 - 3.12, Node.js 18+.

### Cài Đặt Nhanh (Native)

1.  **Tải mã nguồn và cài đặt dependencies**:
    ```bash
    git clone https://github.com/baotri2k6/Open-LLM-DeskAgent.git
    cd Open-LLM-DeskAgent
    npm install
    ```

2.  **Thiết lập môi trường Python**:
    ```bash
    # Tạo virtual environment
    python -m venv venv
    # Kích hoạt venv (Windows)
    .\venv\Scripts\activate
    # Cài đặt thư viện Python
    pip install -r requirements.txt
    ```

3.  **Thiết lập file cấu hình**:
    *   Sao chép tệp `config/companion.config.json.example` thành `config/companion.config.json`.
    *   Nhập các API keys (như Gemini, OpenAI) hoặc chỉnh sửa `llm.provider` thành `"ollama"` nếu muốn chạy offline hoàn toàn.

4.  **Chạy ứng dụng**:
    ```bash
    npm start
    ```
    *(Hệ thống sẽ tự động khởi động Backend Python ở cổng 8765 và khởi chạy giao diện Electron Desktop App)*

### Cài Đặt Bằng Nix (Khuyên dùng cho Linux/macOS)
```bash
nix develop
npm install
pip install -r requirements.txt
npm start
```

### Chạy Sandbox với Docker
```bash
docker-compose up --build
```

---

## 🧪 Chạy Kiểm Thử Toàn Bộ Hệ Thống (46/46 PASS)

Dự án đi kèm bộ kiểm thử tích hợp toàn diện từ Phase 2 đến Phase 9 để xác minh tính ổn định của toàn bộ stack:

```bash
# Chạy tất cả các test suite tích hợp
python tests/test_phase2_companion.py
python tests/test_phase3_agentic.py
python tests/test_phase4_os_world.py
python tests/test_phase5_learning_decision.py
python tests/test_phase6_learning.py
python tests/test_phase7_lifeloop.py
python tests/test_phase8_9_multiagent_evolution.py
```

---

## ⚙️ Cấu HÌnh Mô Hình Ngôn Ngữ (LLM Providers)

DeskAgent hỗ trợ tới 7 nhà cung cấp LLM khác nhau. Bạn có thể thay đổi cấu hình trong `config/companion.config.json`:

*   **Ollama (Offline/Free)**:
    ```json
    "llm": {
      "provider": "ollama",
      "model": "qwen2.5:1.5b",
      "host": "http://127.0.0.1:11434"
    }
    ```
*   **Google Gemini (Tốc độ cao/Có gói miễn phí)**:
    ```json
    "llm": {
      "provider": "gemini",
      "gemini_model": "gemini-2.5-flash",
      "gemini_api_key": "YOUR_GEMINI_API_KEY"
    }
    ```

---

## 📄 Bản Quyền & Đóng Góp

Dự án phát hành dưới giấy phép mã nguồn mở **MIT License**. Chi tiết vui lòng đọc tệp [LICENSE](LICENSE).

Để biết thêm thông tin về tiêu chuẩn viết code và đóng góp cho dự án, vui lòng tham khảo [CONTRIBUTING.md](CONTRIBUTING.md) và [AGENTS.md](AGENTS.md).