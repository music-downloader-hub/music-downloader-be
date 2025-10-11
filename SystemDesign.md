## Kiến trúc mở rộng – Backend Python

- Redis job store & progress - Lưu, chia sẻ trạng thái job - Scale đa instance, phục hồi sau restart - Hash `jobs:{id}`, Hash `jobs:{id}:progress`, List/Stream `jobs:{id}:logs`, TTL key - Redis, redis-py, FastAPI
- Dedupe/Idempotency lock - Chống chạy trùng cùng URL/biến thể - Giảm tải, tiết kiệm tài nguyên - `SETNX lock:{content_key}` với TTL; trả về job hiện có nếu trùng - Redis
- Disk cache TTL + Quota (LRU) - Quản lý dung lượng audio - Không tràn đĩa, vẫn nhanh - TTL `dir:{path}`, ZSET `cache:lru` (last_access), `cache:bytes`, dọn nền và xóa LRU khi vượt quota - Redis + Python scheduler (thread)
- Cleaner nền theo TTL - Dọn thư mục hết hạn - Tối ưu dung lượng - Quét `AM-DL downloads/`, nếu `dir:{path}` không tồn tại trên Redis thì xóa; khóa `lock:dir:{path}` - Python (FastAPI BackgroundTasks/thread)
- SSE/events distribution - Phát sự kiện tiến độ đa process - Realtime, scale ngang - Pub/Sub `jobs:{id}:events` hoặc Streams + XREAD; frontend SSE đọc qua API - Redis Pub/Sub/Streams, FastAPI
- Logs storage & tail - Lưu/tua logs hiệu quả - Giảm RAM, truy vấn nhanh `last_n` - `RPUSH jobs:{id}:logs`, `LTRIM` giữ N dòng; hoặc Streams để phân phối - Redis
- Batch queue & concurrency - Điều tiết số tiến trình CLI - Ổn định tải, tránh nghẽn I/O - Hàng đợi nhẹ bằng Redis List/Streams + worker Python gọi `go run`; cấu hình max concurrency - Redis + Python worker (hoặc RQ/Arq/Celery)
- Archive on-demand & cleanup - Tạo ZIP khi tải về - Tiết kiệm đĩa - Tạo ZIP tạm qua `FileResponse`, xóa bằng `BackgroundTasks` sau khi gửi - FastAPI, `shutil`
- Feature flags & config - Bật/tắt tính năng (Spotify, Redis, cleaner) - An toàn triển khai - Biến môi trường `ENABLE_*`, `REDIS_URL`, `CACHE_MAX_BYTES`, `CACHE_TTL_SECONDS` - dotenv, env vars
- Observability & metrics - Theo dõi hiệu năng, lỗi - Tối ưu vận hành - Counters trong Redis (jobs theo trạng thái), Prometheus exporter, structured logging - Prometheus, Grafana, logfmt/json
- Horizontal scaling - Chạy nhiều instance API/worker - Tăng thông lượng - Stateless API; chia sẻ trạng thái qua Redis; reverse proxy cân bằng tải - Redis, Nginx/Caddy, systemd/Docker
- Security & abuse control - Chống lạm dụng - Ổn định dịch vụ - Rate limit theo IP/API key (token bucket Redis), size/timeouts, sandbox tiến trình CLI - Redis, FastAPI deps/middleware
- Resilience & recovery - Chịu lỗi, tự phục hồi - Giảm downtime - Retry có backoff, phát hiện process zombie, resume trạng thái từ Redis khi API khởi động lại - Redis, psutil
- Optional object storage - Lưu audio ngoài ổ máy - Mở rộng dung lượng - Đưa file nóng lên local cache; nguồn chính S3/MinIO + lifecycle 1–2 ngày - S3/MinIO, boto3/minio-py


