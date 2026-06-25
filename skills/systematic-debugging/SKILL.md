---
name: systematic-debugging
description: "Tìm kiếm lỗi, phân tích nguyên nhân bằng Blame/Log, viết test tái dựng lỗi và sửa chữa."
version: 1.0.0
author: "Antigravity & DeskAgent"
---

# Sửa Lỗi Hệ Thống Lập Trình (Systematic Debugging)

Kỹ năng này hướng dẫn quy trình từng bước để phát hiện, phân tích nguyên nhân gốc rễ của lỗi lập trình (bug) trong dự án, và viết thử nghiệm để kiểm chứng giải pháp sửa lỗi.

## Khi nào nên sử dụng

Sử dụng khi người dùng yêu cầu sửa lỗi code hoặc báo cáo chương trình bị crash:
- "Sửa lỗi crash ở file main.py giúp tớ"
- "Tìm xem tại sao hàm X lại trả về None"
- "Debug lỗi kết nối cơ sở dữ liệu"
- "Tại sao app bị trắng màn hình"

## Cách chạy

Sử dụng kết hợp các công cụ:
- `read_file` để đọc mã nguồn và log lỗi.
- `execute_command` để chạy các script test và lệnh debug.
- `write_to_file` để tạo kịch bản thử nghiệm hoặc sửa mã nguồn.

## Quy trình thực hiện

1. **Thu thập thông tin lỗi (Traceback & Logs):**
   - Đọc kỹ thông báo lỗi (Traceback) từ console hoặc file logs bằng `read_file`.
   - Xác định rõ dòng code gây ra lỗi và tên ngoại lệ (Exception name).

2. **Phân tích lịch sử thay đổi (Chesterton's Fence & Blame):**
   - Trước khi sửa đổi một khối code quan trọng, hãy tìm hiểu lý do tại sao nó được viết như thế:
     - Lệnh: `git blame -L <dòng_bắt_đầu>,<dòng_kết_thúc> <đường_dẫn_tới_file>`
     - Xem commit gần đây chạm vào tệp đó để hiểu ngữ cảnh: `git log -n 5 --patch -- <đường_dẫn_tới_file>`

3. **Viết kịch bản tái tạo lỗi (Reproduce Test):**
   - Tạo một script python nhỏ trong thư mục `scratch/` để chỉ chạy riêng đoạn code bị lỗi với các tham số đầu vào tương tự.
   - Chạy script thử nghiệm bằng `execute_command` để xác nhận lỗi xảy ra đúng như dự đoán (đảm bảo lỗi không phải do tác nhân ngẫu nhiên).

4. **Sửa mã nguồn & Chạy lại thử nghiệm:**
   - Thực hiện sửa mã nguồn bị lỗi bằng `write_to_file` (hoặc `patch`).
   - Chạy lại script thử nghiệm ở bước 3. Xác nhận lỗi đã biến mất hoàn toàn.
   - Chạy bộ kiểm thử (test suite) của dự án (nếu có, ví dụ: `pytest` hoặc `npm test`) để đảm bảo việc sửa chữa không làm hỏng các tính năng cũ khác.

## Vấn đề thường gặp (Pitfalls)
- **Sửa mò không kiểm thử:** Tránh việc đoán nguyên nhân rồi sửa trực tiếp trên file chính mà không chạy thử nghiệm tái dựng trước. Việc này rất dễ làm phát sinh thêm các bug ẩn khác.
- **Bỏ qua log:** Đôi khi log của hệ thống ghi đè nhiều thông tin khác, hãy lọc từ khóa quan trọng như `"ERROR"` hoặc `"Exception"` để khoanh vùng nhanh.

## Xác nhận kết quả
- Script tái tạo lỗi chạy thành công không còn sinh traceback, và toàn bộ test suite của dự án báo xanh.
