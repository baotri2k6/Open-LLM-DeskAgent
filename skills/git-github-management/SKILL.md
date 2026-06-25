---
name: git-github-management
description: "Quản lý mã nguồn, kiểm tra status, commit, tạo branch và đẩy code lên GitHub."
version: 1.0.0
author: "Antigravity & DeskAgent"
---

# Quản Lý Mã Nguồn Git & GitHub

Kỹ năng này hướng dẫn cách sử dụng công cụ dòng lệnh để kiểm tra thay đổi, viết commit chất lượng cao, quản lý nhánh (branch) và đồng bộ mã nguồn với GitHub.

## Khi nào nên sử dụng

Sử dụng khi người dùng yêu cầu các hành động liên quan đến Git/GitHub:
- "Kiểm tra xem có file nào thay đổi không"
- "Commit code hiện tại với nội dung..."
- "Đẩy thay đổi lên github giúp tớ"
- "Tạo nhánh mới tên là..."
- "Xem lịch sử commit gần nhất"

## Cách chạy

Sử dụng công cụ:
- `execute_command` để chạy các lệnh `git` tương ứng.

## Quy trình thực hiện

1. **Kiểm tra trạng thái repository (Status & Diff):**
   - Gọi `execute_command` với lệnh: `git status`
   - Xem các dòng thay đổi bằng: `git diff` (hoặc `git diff --staged` để xem file đã thêm vào index).
   
2. **Thêm và Commit thay đổi (Stage & Commit):**
   - Thêm tệp thay đổi vào index:
     - Thêm tất cả thay đổi: `git add .`
     - Thêm tệp cụ thể: `git add <tên_file>`
   - Commit với thông điệp rõ ràng:
     - Lệnh: `git commit -m "loại_commit: mô tả ngắn gọn về thay đổi"`
     - Ví dụ: `git commit -m "fix: sửa lỗi 429 rate limit trong main_server"`

3. **Quản lý nhánh (Branch):**
   - Xem các nhánh hiện tại: `git branch`
   - Tạo nhánh mới và chuyển sang nhánh đó: `git checkout -b <tên_nhánh>`
   - Chuyển nhánh: `git checkout <tên_nhánh>`

4. **Đẩy mã nguồn lên GitHub (Push & Pull):**
   - Lấy cập nhật mới nhất từ server về: `git pull origin <tên_nhánh>`
   - Đẩy thay đổi mới lên: `git push origin <tên_nhánh>`

## Vấn đề thường gặp (Pitfalls)
- **Xung đột mã nguồn (Merge Conflict):** Nếu `git pull` báo xung đột, hãy dừng lại, đọc nội dung tệp tin bị xung đột, chỉnh sửa để giải quyết xung đột bằng `write_to_file` rồi mới tiếp tục commit.
- **Thiếu thông tin người dùng (Missing User Info):** Nếu git báo lỗi chưa config email/username, hãy gọi lệnh:
  - `git config --global user.email "email@example.com"`
  - `git config --global user.name "Tên Của Bạn"`

## Xác nhận kết quả
- Chạy lệnh `git status` hiển thị dòng thông báo sạch sẽ: *"nothing to commit, working tree clean"* và code đã được đẩy lên GitHub thành công.
