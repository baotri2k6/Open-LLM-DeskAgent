<div align="center">

# 🎀 Open LLM DeskAgent

**AI Companion sống động trên Desktop — Nghe, Nói, Nhớ, Biểu cảm và Tự trị Lập trình.**

*Lấy cảm hứng từ Neuro-sama. Chạy hoàn toàn cục bộ (offline/local) hoặc qua API đám mây.*

[![Version](https://img.shields.io/badge/version-0.2.0-purple?style=for-the-badge)](https://github.com/baotri2k6/Open-LLM-DeskAgent)
[![License](https://img.shields.io/badge/license-MIT-orange?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=for-the-badge)](#)
[![Python](https://img.shields.io/badge/python-3.10+-yellow?style=for-the-badge)](https://www.python.org)
[![Node](https://img.shields.io/badge/node-18+-green?style=for-the-badge)](https://nodejs.org)

---

**Open LLM DeskAgent** không chỉ đơn thuần là một chatbot hay một widget máy tính vô hồn. Đây là một **AI Companion thực sự sống trên màn hình của bạn** dưới dạng avatar tương tác trực quan (Live2D/Spine). Dự án kết hợp các mô hình ngôn ngữ lớn (LLM), thị giác máy tính (VLM), tổng hợp giọng nói tự nhiên (TTS), và bộ nhớ dài hạn cục bộ để tạo ra một thực thể có cá tính, cảm xúc, có khả năng tự nhận thức màn hình và trực tiếp giúp bạn điều khiển máy tính.

</div>

---

## ✨ Các Tính Năng Nổi Bật

### 🧠 1. Vòng lặp Nhận thức Tự trị (Cognitive & Autonomous Loop)
*   **Cognitive Loop**: Mô hình hoạt động theo chu trình khép kín: *Nhận thức (Perception) → Ký ức (Memory) → Cảm xúc (Emotion) → Suy nghĩ (Cognition) → Hành động (Action)*.
*   **Proactive Interaction**: Nhân vật tự động chụp ảnh màn hình, tự nhận xét về những gì bạn đang làm và chủ động lên tiếng phá vỡ im lặng nếu bạn treo máy quá lâu (> 3 phút).
*   **Barge-in (Nói đè)**: Hệ thống VAD (Voice Activity Detection) giám sát thời gian thực. Khi AI đang nói, bạn có thể nói chen vào; AI sẽ lập tức dừng phát âm thanh để lắng nghe bạn.

### 🎭 2. Hoạt ảnh Tương tác Trực quan (Live2D & Spine)
*   **4 Nhân vật Live2D độc đáo**: *IceGirl* (lém lỉnh, trêu chọc), *Hiyori* (năng động, tươi cười), *Mao* (Tsundere thời trang), và *Huohuo* (phán quan nhút nhát).
*   **WebGL Click-Through**: Khả năng chạm xuyên vật thể thông minh. Hệ thống tự động đọc kênh Alpha của WebGL context tại vị trí con trỏ chuột. Cửa sổ Electron sẽ bỏ qua chuột (ignore mouse events) khi cursor nằm trên các vùng trong suốt và chỉ nhận tương tác khi bạn click trực tiếp vào cơ thể nhân vật.
*   **Lipsync & Emotion Realtime**: Phân tích tần số âm thanh thời gian thực để tạo khẩu hình nhép miệng (lipsync) khớp với giọng nói. Tự động chuyển đổi biểu cảm khuôn mặt tương ứng với nhãn cảm xúc sinh ra từ LLM.

### 💾 3. Ký ức Dài Hạn Cục Bộ (Hybrid Vector Memory)
*   **PGlite WASM Database**: Cơ sở dữ liệu Postgres WASM lưu trữ bền vững ngay trong trình duyệt Electron (IndexedDB).
*   **Local Embeddings**: Sử dụng `@huggingface/transformers` tải mô hình nhúng `all-MiniLM-L6-v2` (~90MB) để tính toán vector và tìm kiếm ngữ nghĩa (semantic search) hoàn toàn offline.
*   **Nhật ký Tự trị**: Tự động đúc kết lịch sử trò chuyện hàng ngày thành các trang nhật ký dưới góc nhìn thứ nhất của nhân vật và lưu trữ vào Vector DB để làm bối cảnh gợi nhớ lâu dài.

### 🛠️ 4. Điều khiển Máy tính Bằng Thị giác (Computer Use)
*   **UI-TARS Grounding**: Sử dụng các mô hình thị giác (VLM) để định vị và nhấp chuột vào bất kỳ phần tử nào trên màn hình thông qua tọa độ chuẩn hóa `[0, 1000]`, không phụ thuộc vào DOM hay tọa độ cứng.
*   **Hành động mượt mà**: Di chuyển chuột trượt dần tự nhiên (`pyautogui.moveTo` với duration), tự động chờ trình duyệt tải trang trước khi thao tác tiếp theo.
*   **Hệ thống Phân quyền An toàn**: `PermissionManager` kiểm soát các lệnh nguy hại thông qua cơ chế duyệt trước (như chạy shell script, chỉnh sửa tệp tin hệ thống). Chế độ `trust_workspace` tự động duyệt các lệnh an toàn cục bộ.

### 🔌 5. Plugin SDK & MCP & OBS Stream Kit
*   **Plugin SDK**: Cho phép mở rộng tính năng dễ dàng bằng Python. Các plugin mặc định đi kèm: *Cờ vua* (tự chơi/đánh với người), *Nhà thông minh* (kết nối Home Assistant thật hoặc giả lập), và *Web Reader* (sử dụng Jina Reader/BeautifulSoup4).
*   **Model Context Protocol (MCP)**: Hỗ trợ kết nối động các tool servers theo chuẩn của Anthropic.
*   **OBS Stream Kit**: Tích hợp WebSocket Server (Port 9001) phát sóng trực tiếp trạng thái nhân vật, Lipsync, lời thoại và suy nghĩ lên màn hình OBS Browser Source phục vụ streamer ảo.

### 💻 6. Môi trường Chuyên nghiệp cho Nhà phát triển
*   **Nix Flake (`flake.nix`)**: Tạo lập môi trường phát triển nhất quán 100% (cài sẵn Python, Node, Electron) chỉ với một lệnh `nix develop`.
*   **Docker Sandbox**: Hỗ trợ chạy toàn bộ backend Python và công cụ trong container Docker để cách ly an toàn với máy chủ.
*   **Autonomous SWE-Runner**: Lõi tác nhân kỹ sư phần mềm tự trị (`mini_swe_runner.py`). Agent tự động tìm kiếm file lỗi, viết code sửa đổi, chạy unit tests (`pytest`), và tự sửa lỗi nếu test fail.

---

## 📐 Kiến Trúc Dự Án

Thư mục dự án được tổ chức theo cấu trúc phẳng theo đặc tính (Domain/Feature) của hệ thống:

```text
Open-LLM-DeskAgent/
├── runtime/                 # AI Runtime Kernel (vòng đời, state, scheduler)
├── life/                    # Nhịp sinh hoạt tự trị của Companion
├── perception/              # Thu thập dữ liệu đầu vào (voice, screen, vision)
├── persona/                 # Cá tính, cảm xúc, biểu cảm Live2D/Spine
├── memory/                  # Hệ thống ký ức (working, episodic, semantic)
├── cognition/               # Lớp suy luận logic (AI Reasoning, planner)
├── agents/                  # Các Agent chuyên biệt (browser, coding, desktop...)
├── execution/               # Thao tác hệ thống (keyboard, mouse, browser)
├── tools/                   # Công cụ hệ thống cơ bản (tools/registry.py)
├── llm/                     # LLM Gateway (providers, prompts, parser)
├── speech/                  # STT + TTS Pipelines (whisper, funasr, edge...)
├── vision/                  # Vision Pipeline (ocr, grounding, screen understanding)
├── desktop/                 # Electron Main Process (ipc, windows, tray)
├── renderer/                # Electron Renderer UI (avatar, chat, settings)
├── live2d/                  # Live2D Runtime
├── api/                     # HTTP/WebSocket Server
├── config/                  # Tệp cấu hình hệ thống
├── database/                # SQLite, VectorDB layers
├── assets/                  # Live2D models, icons, images
├── scripts/                 # Build & start scripts
└── tests/                   # Kịch bản kiểm thử
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

3.  **Khởi chạy cấu hình mẫu**:
    *   Tạo file cấu hình thật từ file mẫu: Sao chép tệp `config/companion.config.json.example` thành `config/companion.config.json`.
    *   Nhập các API keys (như Gemini, OpenAI) hoặc chỉnh sửa `llm.provider` thành `"ollama"` nếu muốn chạy offline hoàn toàn.

4.  **Chạy ứng dụng**:
    ```bash
    npm start
    ```
    *(Lệnh này sẽ tự động khởi động Backend Python ở cổng 8765 và khởi chạy giao diện Electron Desktop App)*

### Cài Đặt Bằng Nix (Khuyên dùng cho Linux/macOS)
Nếu máy tính của bạn đã cài đặt Nix package manager:
```bash
nix develop
npm install
pip install -r requirements.txt
npm start
```

### Chạy Sandbox với Docker
Để chạy backend Python độc lập trong môi trường Docker:
```bash
docker-compose up --build
```

---

## ⚙️ Cấu Hình Mô Hình Ngôn Ngữ (LLM Providers)

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
*   **DeepSeek, OpenAI, Qwen, GLM**: Nhập API Key tương ứng vào cấu hình json để sử dụng.

---

## 📖 Hướng Dẫn Phát Triển Kỹ Năng & Plugins

### Cách tạo thêm một Kỹ năng (Skill) mới
Skills giúp mô hình biết cách thực hiện các tác vụ quy chuẩn bằng hướng dẫn dạng Markdown.
1.  Tạo thư mục mới trong `skills/`: `skills/my-new-task/`.
2.  Tạo tệp `SKILL.md` bên trong thư mục đó với YAML frontmatter bắt buộc:
    ```markdown
    ---
    name: my-new-task
    description: Hướng dẫn Agent cách thực hiện tác vụ của bạn.
    ---
    # Hướng dẫn thực hiện tác vụ
    1. Đầu tiên hãy gọi công cụ...
    2. Sau đó đọc kết quả và...
    ```
3.  Khi khởi động, `SkillsManager` sẽ tự động phát hiện và huấn luyện (inject) kỹ năng này vào prompt của DeskAgent.

### Cách chạy thử nghiệm SWE-Runner tự trị
Để kiểm chứng khả năng tự sửa lỗi lập trình của Agent:
```bash
python agents/coding/mini_swe_runner.py "Sửa lỗi hàm tính tổng trong file calculator.py" "./tests/sandbox"
```
Agent sẽ tự động đọc thư mục test sandbox, tìm lỗi, viết lại code, chạy kiểm thử, và tự sửa tiếp nếu test thất bại.

---

## 📄 Bản Quyền & Đóng Góp

Dự án phát hành dưới giấy phép mã nguồn mở **MIT License**. Chi tiết vui lòng đọc tệp [LICENSE](LICENSE).

Để biết thêm thông tin về tiêu chuẩn viết code và đóng góp cho dự án, vui lòng tham khảo [CONTRIBUTING.md](CONTRIBUTING.md) và [AGENTS.md](AGENTS.md).