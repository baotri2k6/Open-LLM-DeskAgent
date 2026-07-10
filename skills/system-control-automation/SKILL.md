---
name: system-control-automation
description: "Quản lý trạng thái hệ thống, hẹn giờ tắt máy, và điều khiển nguồn điện."
version: 1.0.0
author: "Antigravity & DeskAgent"
---

# Tự Động Hóa Điều Khiển Hệ Thống & Tắt Máy

Kỹ năng này hướng dẫn cách thực thi các lệnh hệ điều hành liên quan đến quản lý nguồn điện (tắt máy, khởi động lại) và hẹn giờ tự động tắt máy theo yêu cầu của người dùng.

## Khi nào nên sử dụng

Sử dụng khi người dùng yêu cầu điều khiển trạng thái máy tính:
- "Tắt máy tính giúp tớ"
- "Hẹn giờ 1 phút nữa tắt máy tính"
- "Làm xong việc thì tắt máy nhé"
- "Hủy hẹn giờ tắt máy đi"

## Cách chạy

Sử dụng công cụ:
- `execute_command` để chạy lệnh tương ứng trên Windows shell (cmd/powershell).

## Quy trình thực hiện

1. **Hẹn giờ tắt máy (Delayed Shutdown):**
   - Công thức quy đổi: Đổi thời gian người dùng yêu cầu ra đơn vị giây (\(s\)).
     - 1 phút = 60 giây.
     - 5 phút = 300 giây.
     - 1 tiếng = 3600 giây.
   - Gọi công cụ `execute_command` với lệnh:
     - Windows: `shutdown /s /t <số_giây>` (Ví dụ: `shutdown /s /t 60` để hẹn giờ tắt máy sau 1 phút).
   - Phản hồi ngắn gọn xác nhận với người dùng thời gian máy tính sẽ tự động tắt.

2. **Tắt máy ngay lập tức:**
   - Gọi công cụ `execute_command` với lệnh:
     - Windows: `shutdown /s /f /t 0` (Buộc đóng ứng dụng và tắt máy ngay lập tức).

3. **Hủy lệnh hẹn giờ tắt máy:**
   - Nếu người dùng muốn đổi ý hoặc hủy lệnh tắt máy đã lên lịch:
   - Gọi công cụ `execute_command` với lệnh:
     - Windows: `shutdown /a` (Hủy bỏ lệnh tắt máy đang chờ).
   - Phản hồi xác nhận đã hủy thành công.

## Vấn đề thường gặp (Pitfalls)
- **Quyền Admin:** Một số lệnh hệ thống yêu cầu quyền cao hơn, tuy nhiên lệnh `shutdown` thông thường trên Windows không yêu cầu quyền Admin của người dùng để thực thi cho chính phiên đăng nhập đó.
- **Lưu trữ dữ liệu:** Hãy luôn nhắc nhở người dùng lưu lại các tệp làm việc trước khi thực hiện lệnh tắt máy ngay lập tức.

## Xác nhận kết quả
- Windows hiển thị một thông báo hệ thống nhỏ báo hiệu máy tính sẽ tắt sau thời gian đã lên lịch (hoặc thông báo hủy bỏ lịch tắt máy thành công).
