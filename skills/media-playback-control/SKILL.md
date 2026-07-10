---
name: media-playback-control
description: "Mở trình duyệt, tìm kiếm và phát nhạc tự động trên YouTube."
version: 1.0.0
author: "Antigravity & DeskAgent"
---

# Điều Khiển Phát Nhạc & Trình Duyệt Tự Động

Kỹ năng này hướng dẫn tác nhân cách mở trình duyệt mặc định, truy cập YouTube, tìm kiếm bài hát theo yêu cầu của người dùng và nhấp phát nhạc tự động bằng thị giác.

## Khi nào nên sử dụng

Sử dụng khi người dùng yêu cầu các lệnh liên quan đến phát nhạc, bật bài hát, hoặc tìm video:
- "Mở nhạc của Sơn Tùng M-TP"
- "Bật nhạc thư giãn trên YouTube"
- "Tìm bài hát đi"
- "Vào youtube nghe nhạc"

## Cách chạy

Sử dụng kết hợp các công cụ:
- `open_url` để mở trực tiếp trang tìm kiếm hoặc trang chủ YouTube.
- `click_element_by_vision` để nhấp vào thanh tìm kiếm hoặc kết quả video đầu tiên.
- `keyboard_type` để nhập tên bài hát.
- `keyboard_press` để nhấn Enter.

## Quy trình thực hiện

1. **Mở trang YouTube:**
   - Ưu tiên sử dụng `open_url` với liên kết cụ thể:
     - Nếu người dùng yêu cầu bài hát cụ thể (ví dụ: "nhạc Sơn Tùng"): gọi `open_url` với link tìm kiếm trực tiếp: `https://www.youtube.com/results?search_query=nhạc+Sơn+Tùng+M-TP`
     - Nếu người dùng chỉ nói "mở nhạc/youtube": gọi `open_url("https://youtube.com")`
   - Đợi 2 giây để trình duyệt tải xong trang.

2. **Tìm kiếm (nếu chưa tìm kiếm trực tiếp qua URL):**
   - Sử dụng `click_element_by_vision` với mô tả: `"Thanh tìm kiếm của YouTube"` hoặc `"search box"`.
   - Sử dụng `keyboard_type` nhập tên bài hát người dùng muốn nghe.
   - Sử dụng `keyboard_press` với tham số `keys="enter"`.

3. **Chọn và phát video:**
   - Chụp ảnh màn hình mới (hệ thống tự động đính kèm ở lượt thoại tiếp theo).
   - Nhận diện video đầu tiên hiển thị trên màn hình.
   - Sử dụng `click_element_by_vision` với mô tả: `"Kết quả video đầu tiên"` hoặc `"Hình thu nhỏ của video nhạc đầu tiên"`.

## Vấn đề thường gặp (Pitfalls)
- **Trình duyệt chưa tải xong:** Nếu chụp ảnh quá sớm khi trang chưa tải xong, AI sẽ không nhìn thấy kết quả. Hãy luôn đợi trang hiển thị đầy đủ.
- **Có quảng cáo:** Nếu bài hát có quảng cáo trước video, AI không cần làm gì thêm, nhạc sẽ tự phát sau khi quảng cáo kết thúc.

## Xác nhận kết quả
- Video nhạc được phát thành công trên trình duyệt mặc định của người dùng và có âm thanh phát ra.
