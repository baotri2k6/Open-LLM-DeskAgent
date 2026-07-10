# Hướng dẫn đóng góp vào DeskAgent (Contributing Guidelines)

Chào mừng bạn đến với **DeskAgent**! Dự án hiện đã bước sang giai đoạn mới với kiến trúc Hybrid (TypeScript Electron + Python Backend AI Runtime) hoàn thiện, hỗ trợ vòng lặp tự trị (Life Loop), cơ sở dữ liệu ký ức độc lập và các nhà cung cấp mô hình (LLM Providers) được mô-đun hóa.

Để giữ chất lượng mã nguồn cao và nhất quán, vui lòng đọc kỹ hướng dẫn dưới đây trước khi tạo pull request.

---

## 1. Thiết lập Môi trường Phát triển (Local Setup)

Dự án yêu cầu cài đặt sẵn Node.js (v18+) và Python (3.10+).

### Bước 1: Thiết lập Renderer & Desktop UI (Node.js)
1. Cài đặt các thư viện Node:
   ```bash
   npm install
   ```
2. Biên dịch TypeScript cho Renderer và Main Process:
   ```bash
   npm run build-ts
   ```
3. Chạy ứng dụng Electron ở chế độ phát triển (sẽ tự động biên dịch lại khi thay đổi code):
   ```bash
   npm run dev
   ```

### Bước 2: Thiết lập Bộ não AI (Python Backend)
1. Khởi tạo và kích hoạt môi trường ảo:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```
2. Cài đặt các thư viện Python:
   ```bash
   pip install -r requirements.txt
   ```
3. Khởi chạy máy chủ API local (nếu không chạy thông qua tiến trình Electron tự kích hoạt):
   ```bash
   python api/server.py
   ```

---

## 2. Tiêu chuẩn Mã nguồn & Cấu trúc Thư mục

Mã nguồn được tổ chức theo tính chất phân lớp nghiêm ngặt. Khi phát triển tính năng mới, vui lòng tuân thủ:

### Giao diện (src/desktop/ & src/renderer/)
*   **src/desktop/**: Toàn bộ Main Process, điều phối IPC, quản lý cửa sổ và tích hợp hệ điều hành. Phải viết bằng **TypeScript** với kiểu dữ liệu đầy đủ.
*   **src/renderer/**: Chứa mã nguồn Renderer Process (HTML, CSS, logic WebGL/PixiJS). Không chạy trực tiếp shell lệnh OS hay script Python từ renderer; toàn bộ giao tiếp phải đi qua cầu nối IPC trong Preload script.
*   **esbuild compilation**: Mã nguồn TypeScript sẽ tự động được esbuild biên dịch từ `src/` ra `desktop/` và `renderer/` để Electron sử dụng. Không chỉnh sửa trực tiếp các file JS trong thư mục gốc `desktop/` hay `renderer/`.

### Bộ não AI (backend/)
*   **llm/providers/**: Khi tích hợp một nhà cung cấp LLM mới (ví dụ: Claude, Gemini-next), hãy tạo class kế thừa từ `BaseLLMProvider` trong `llm/providers/base.py` và lưu tại thư mục này. Tránh viết trực tiếp các hàm gọi HTTP dạng monolith vào `llm/manager.py`.
*   **cognition/**: Tầng điều phối tư duy chính. Mọi logic tương tác liên quan đến RAG, đúc kết bộ nhớ dài hạn và cập nhật cảm xúc tự trị phải được gọi tập trung tại `CognitionEngine`.
*   **memory/**: Hệ thống ký ức tự trị (Working Memory, Episodic Memory, và Long-term Memory). Sử dụng `ChromaMemoryStore` từ `memory/vectorstore/chroma_store.py` để ghi nhớ thông tin độc lập với dữ liệu tài liệu RAG.

---

## 3. Tạo Kỹ năng (Skills) & Plugin mới

### Tạo Kỹ năng (Skills)
Skills là các tập tin markdown nằm tại `skills/<tên_kỹ_năng>/SKILL.md` hướng dẫn AI thực thi tác vụ hệ thống.
*   Mỗi kỹ năng phải chứa phần YAML frontmatter ở đầu để hệ thống tự động đăng ký:
    ```yaml
    ---
    name: ten-ky-nang
    description: Mô tả ngắn gọn về tác dụng của kỹ năng này để LLM quyết định gọi khi cần.
    ---
    ```

### Tạo Plugin
Plugins mở rộng tính năng hệ thống bằng Python functions.
*   Lưu tại `plugins/<tên_plugin>/`.
*   Phải chứa định nghĩa `plugin.json` định cấu hình schema để nạp động.
*   Tất cả dữ liệu sinh ra bởi plugin phải được lưu trong thư mục `cache/` hoặc `data/` cục bộ.

---

## 4. Quy trình Đóng góp & Kiểm định (Testing)

Trước khi gửi pull request hoặc bàn giao code, bạn **bắt buộc** phải đảm bảo bộ unit test kiểm tra kiến trúc đi qua thành công:
```bash
python tests/test_milestones_completion.py
```
Bộ test sẽ tự động xác thực:
*   Độ phủ và khả năng nạp của tất cả stubs, managers, providers, và databases.
*   Độ trễ và tính chính xác của EventBus cùng bộ nạp cấu hình hệ thống.

Nếu có bất kỳ lỗi test nào bị `[FAIL]`, vui lòng sửa chữa trước khi đẩy code lên nhánh chính.

Cảm ơn bạn đã đồng hành đóng góp xây dựng người bạn ảo thông minh DeskAgent!
