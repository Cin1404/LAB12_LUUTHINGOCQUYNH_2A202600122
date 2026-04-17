Tên sinh viên: Lưu Thị Ngọc Quỳnh
Mã sinh viên: 2A202600122
Ngày: 17/04/2026

# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Các anti-pattern tìm được
1. API key bị hardcode trong source code.
2. Database URL bị hardcode trong source code.
3. Cấu hình như `DEBUG`, `MAX_TOKENS`, `PORT` không lấy từ environment variables.
4. Dùng `print()` để log và còn làm lộ secret trong log.
5. Không có health check endpoint.
6. Server chỉ chạy với `localhost`, không phù hợp khi deploy.
7. Port bị cố định là `8000`.
8. Bật `reload=True`, chỉ phù hợp cho môi trường development.
9. Không có xử lý graceful shutdown khi ứng dụng bị dừng.

### Exercise 1.3: Bảng so sánh

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode | Env vars | Dễ đổi cấu hình theo từng môi trường, an toàn hơn khi deploy |
| Health check | Không có | Có `/health` và `/ready` | Giúp hệ thống kiểm tra app còn sống và sẵn sàng nhận request |
| Logging | `print()` | JSON logging | Dễ theo dõi, tìm lỗi và quản lý log trong production |
| Shutdown | Đột ngột | Graceful shutdown | Giúp app tắt an toàn, không làm mất request đang xử lý |
| Host/Port | Cố định `localhost:8000` | Lấy từ config/env | Phù hợp khi chạy trên Docker, Railway, Render |
| Debug | `reload=True` | Chỉ bật khi cần | Tránh ảnh hưởng hiệu năng và ổn định trong production |
| Secrets | Hardcode trong code | Tách khỏi code | Giảm nguy cơ lộ thông tin nhạy cảm |

...

## Part 2: Docker

### Exercise 2.1: Câu hỏi về Dockerfile

1. Base image là `python:3.11`.
2. Working directory là `/app`.
3. `COPY requirements.txt` trước để tận dụng Docker layer cache. Nếu requirements không đổi thì Docker không cần cài lại dependencies mỗi lần build.
4. `CMD` dùng để chỉ lệnh mặc định khi container chạy. `ENTRYPOINT` dùng để cố định lệnh chính của container. Nói ngắn gọn, `CMD` dễ bị ghi đè hơn, còn `ENTRYPOINT` thường dùng khi muốn container luôn chạy theo một chương trình cụ thể.


### Exercise 2.3: So sánh kích thước image
- Develop: [X] MB
- Production: [Y] MB
- Chênh lệch: [Z]%

## Part 3: Cloud Deployment

### Exercise 3.1: Deploy Railway
- URL: https://your-app.railway.app
- Ảnh chụp màn hình: [Link ảnh trong repo]

## Part 4: API Security

### Exercise 4.1-4.3: Kết quả test
[Dán output test của bạn]

### Exercise 4.4: Phần cài đặt Cost Guard
[Giải thích cách bạn triển khai]

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Ghi chú triển khai
[Giải thích và kết quả test của bạn]
