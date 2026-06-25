---
name: productivity-notion
description: "Đồng bộ hóa, truy xuất và quản lý cơ sở dữ liệu, trang Notion thông qua API và lệnh curl."
version: 1.0.0
author: "DeskAgent & Hermes"
---

# Kỹ năng tích hợp năng suất với Notion API

Kỹ năng này hướng dẫn tác nhân cách thực hiện các thao tác đọc, viết, cập nhật dữ liệu trên trang và cơ sở dữ liệu (Database) của Notion thông qua các yêu cầu HTTP (sử dụng lệnh `curl` trong Shell).

## Khi nào nên sử dụng

Sử dụng khi người dùng muốn tự động hóa Notion, cập nhật danh sách công việc (todo list), thêm ghi chú hoặc truy vấn cơ sở dữ liệu trên Notion:
- "Thêm một công việc mới vào Notion"
- "Lấy danh sách các task hôm nay từ Notion"
- "Đồng bộ hóa ghi chú này lên Notion giúp tôi"

## Cách thiết lập thông tin kết nối

1. Notion yêu cầu mã thông báo API (API Token) và ID của Trang/Cơ sở dữ liệu:
   - Mã thông báo: Thường được lưu trữ trong cấu hình môi trường dưới biến `NOTION_API_KEY` hoặc cấu hình DeskAgent.
   - Database ID: ID của cơ sở dữ liệu mục tiêu (chuỗi 32 ký tự trong URL cơ sở dữ liệu Notion).
2. Hãy kiểm tra biến môi trường hoặc cấu hình trước khi gửi lệnh. Nếu chưa có, hãy lịch sự đề nghị người dùng cung cấp hoặc hướng dẫn họ tạo integration tại `notion.so/my-integrations`.

## Cách thực hiện cuộc gọi API qua Curl

Do DeskAgent chạy trên môi trường có shell (Windows cmd/powershell), cách tốt nhất để gọi Notion API là sử dụng lệnh `curl`.

1. **Truy vấn cơ sở dữ liệu (Query Database):**
   ```bash
   curl -X POST "https://api.notion.com/v1/databases/<DATABASE_ID>/query" \
     -H "Authorization: Bearer <NOTION_API_KEY>" \
     -H "Notion-Version: 2022-06-28" \
     -H "Content-Type: application/json"
   ```

2. **Tạo trang mới trong Database (Create Page):**
   ```bash
   curl -X POST "https://api.notion.com/v1/pages" \
     -H "Authorization: Bearer <NOTION_API_KEY>" \
     -H "Notion-Version: 2022-06-28" \
     -H "Content-Type: application/json" \
     --data "{\"parent\":{\"database_id\":\"<DATABASE_ID>\"},\"properties\":{\"Name\":{\"title\":[{\"text\":{\"content\":\"<Task Name>\"}}]}}}"
   ```

## Quy trình thực hiện

1. **Đọc khóa cấu hình:** Tìm `NOTION_API_KEY` từ file `.env` hoặc file cấu hình cục bộ của DeskAgent.
2. **Chuẩn bị payload JSON:** Thiết kế payload JSON tương ứng với các thuộc tính (properties) của Database Notion của người dùng.
3. **Thực thi qua shell:** Gọi công cụ `execute_command` chạy lệnh `curl` được định dạng chính xác. Luôn xử lý thoát các dấu ngoặc kép `\"` trên Windows.
4. **Phân tích kết quả:** Trích xuất kết quả JSON trả về để phản hồi cho người dùng.

## Vấn đề thường gặp (Pitfalls)
- **Thiếu quyền truy cập trang:** Đảm bảo trang hoặc Database đã được "Share" với Integration của Notion (kết nối API), nếu không sẽ bị báo lỗi 404 hoặc 403.
- **Thoát ký tự đặc biệt trên Windows:** Trên PowerShell hoặc CMD, việc thoát các chuỗi JSON lồng nhau trong lệnh curl rất dễ lỗi. Ưu tiên ghi payload ra một file tạm `temp_payload.json` trước bằng `write_to_file`, sau đó chạy:
  `curl -X POST ... --data @temp_payload.json` để đảm bảo độ tin cậy 100%.
