---
name: note-taking-obsidian
description: "Quản lý và tương tác ghi chú markdown trong Obsidian Vault của người dùng."
version: 1.0.0
author: "DeskAgent & Hermes"
---

# Kỹ năng ghi chú thông minh với Obsidian Vault

Kỹ năng này hướng dẫn tác nhân cách đọc, tìm kiếm, tạo và cập nhật các ghi chú markdown trực tiếp trong thư mục Obsidian Vault của người dùng.

## Khi nào nên sử dụng

Sử dụng khi người dùng yêu cầu các hành động liên quan đến việc ghi chú, quản lý kiến thức cá nhân, hoặc quản lý Obsidian:
- "Ghi chép lại ý tưởng này vào Obsidian giúp tôi"
- "Tìm kiếm các ghi chú về dự án DeskAgent trong Obsidian"
- "Đọc nội dung ghi chú kế hoạch tuần này trong Obsidian"
- "Tạo một ghi chú mới tên là Nhật ký học tập"

## Cách chạy

Sử dụng các công cụ:
- `read_file` để đọc nội dung của một ghi chú cụ thể.
- `write_to_file` để tạo mới hoặc ghi đè ghi chú.
- `execute_command` để chạy các lệnh tìm kiếm hoặc liệt kê tệp nếu cần (ví dụ: dùng `dir` hoặc `findstr`).

## Cách xác định đường dẫn Vault

1. Mặc định Obsidian Vault thường nằm ở đường dẫn:
   - Windows: `C:\Users\<Username>\Documents\Obsidian Vault` hoặc `C:\Users\<Username>\Obsidian`
   - Nếu không chắc chắn, hãy kiểm tra hoặc hỏi người dùng ở lượt đầu tiên (nếu không tự tìm thấy) hoặc thực hiện tìm kiếm qua lệnh shell.
2. Tất cả các đường dẫn tương đối của ghi chú cần được quy đổi thành đường dẫn tuyệt đối trước khi gọi công cụ tệp tin (ví dụ: `Obsidian Vault/Project/Idea.md` -> quy đổi thành đường dẫn tuyệt đối đầy đủ).

## Quy trình thực hiện

1. **Tạo ghi chú mới:**
   - Xác định đường dẫn tuyệt đối cho ghi chú mới (ví dụ: `C:\Users\Nguyen Tri\Documents\Obsidian Vault\Notebook\TenGhiChu.md`).
   - Tạo thư mục cha nếu cần.
   - Gọi `write_to_file` với nội dung markdown thích hợp, luôn sử dụng định dạng chữ viết sạch sẽ, có tiêu đề `#` rõ ràng.

2. **Tìm kiếm ghi chú:**
   - Sử dụng lệnh shell `dir /s /b *.md` trong thư mục Vault để liệt kê toàn bộ ghi chú.
   - Hoặc gọi lệnh `findstr /s /i "từ_khóa" *.md` để tìm nội dung bên trong các ghi chú.

3. **Cập nhật ghi chú:**
   - Luôn đọc ghi chú trước bằng `read_file` để tránh mất dữ liệu cũ.
   - Ghép thêm thông tin mới một cách logic (thường là ở cuối tệp hoặc dưới tiêu đề thích hợp) rồi ghi đè lại bằng `write_to_file`.

## Vấn đề thường gặp (Pitfalls)
- **Lỗi mã hóa tiếng Việt:** Luôn đảm bảo ghi và đọc bằng định dạng UTF-8.
- **Thư mục chưa tồn tại:** Nếu ghi chú nằm trong thư mục con mới tạo, hãy chạy lệnh tạo thư mục trước hoặc đảm bảo công cụ tự động tạo (ở Windows, `write_to_file` sẽ tự tạo thư mục cha).
