---
name: software-development-plan
description: "Chế độ lập kế hoạch (Plan Mode) dành cho các nhiệm vụ phần mềm và kiến trúc phức tạp."
version: 1.0.0
author: "DeskAgent & Hermes"
---

# Chế độ Lập Kế hoạch Phát triển Phần mềm (Plan Mode)

Kỹ năng này hướng dẫn tác nhân cách hoạt động ở chế độ Lập kế hoạch nghiêm ngặt. Khi chế độ này được kích hoạt, tác nhân tập trung phân tích mã nguồn, thiết kế kiến trúc và viết ra một tài liệu kế hoạch chi tiết, tuyệt đối KHÔNG thực thi các lệnh ghi đè tệp hoặc chạy shell làm thay đổi hệ thống.

## Khi nào nên sử dụng

Sử dụng khi người dùng đưa ra các yêu cầu phát triển phần mềm phức tạp, sửa đổi kiến trúc, tích hợp thư viện mới hoặc sửa lỗi hệ thống trên diện rộng:
- "Hãy thiết kế hệ thống chat đa kênh cho dự án này"
- "Viết kế hoạch tích hợp cơ sở dữ liệu mới"
- "Tìm cách cấu trúc lại phần backend để tăng tốc độ"

## Cách hoạt động (Strict Plan Mode)

1. **Giai đoạn nghiên cứu (Research Phase):**
   *   Chỉ sử dụng các công cụ đọc thông tin như `read_file`, `search_google`, `read_webpage_jina` để khảo sát mã nguồn hiện có.
   *   Tuyệt đối KHÔNG sử dụng `write_to_file` (để sửa mã nguồn hiện tại) hoặc `execute_command` (để chạy build/test/run) trong giai đoạn này.
2. **Giai đoạn xuất bản kế hoạch:**
   *   Tạo một tệp kế hoạch markdown mới tại thư mục `plans/` hoặc gốc dự án có tên dạng: `plans/YYYY-MM-DD-plan-<description>.md`.
   *   Nội dung tệp kế hoạch phải mô tả: Mục tiêu, Hiện trạng mã nguồn, Các thay đổi chi tiết từng file, Kế hoạch kiểm thử (Verification Plan).
3. **Dừng và xin phê duyệt:**
   *   Sau khi viết xong tệp kế hoạch, tác nhân phải dừng cuộc hội thoại và lịch sự hiển thị kế hoạch cho người dùng duyệt. Không tự ý sửa đổi code cho đến khi người dùng đồng ý.

## Cấu trúc của một Tệp Kế hoạch tiêu chuẩn

Mỗi kế hoạch xuất ra tệp markdown cần tuân theo cấu trúc sau:

```markdown
# Kế hoạch: [Tên Nhiệm Vụ]

## 1. Mục tiêu & Hiện trạng
- Mô tả ngắn gọn nhiệm vụ cần làm.
- Hiện trạng các file liên quan.

## 2. Các thay đổi đề xuất
- **[MODIFY]** `path/to/file.py`: Mô tả thay đổi.
- **[NEW]** `path/to/new_file.py`: Mô tả mục đích file mới.

## 3. Chi tiết thực thi (Pseudocode / Thiết kế)
- Các hàm/lớp sẽ được sửa hoặc thêm mới.

## 4. Kế hoạch kiểm thử (Verification Plan)
- Cách chạy test tự động (ví dụ: `pytest tests/test_abc.py`).
- Cách kiểm tra thủ công.
```

## Vấn đề thường gặp (Pitfalls)
- **Nôn nóng sửa code:** Tác nhân rất dễ bị lôi cuốn vào việc sửa đổi trực tiếp các file mã nguồn trước khi lập kế hoạch. Hãy luôn tuân thủ nguyên tắc: *Lập kế hoạch trước, code sau*.
