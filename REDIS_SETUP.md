# Redis Setup & Redis Insight Connection Guide

## 1. Cài đặt Redis

### Windows (Docker - Khuyến nghị)
```bash
# Chạy Redis container
docker run -d --name redis-server -p 6379:6379 redis:7-alpine

# Kiểm tra Redis đang chạy
docker ps
```

### Windows (Redis for Windows)
1. Tải Redis for Windows từ: https://github.com/microsoftarchive/redis/releases
2. Giải nén và chạy `redis-server.exe`
3. Mặc định port: 6379

### Linux/macOS
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install redis-server

# macOS (Homebrew)
brew install redis
brew services start redis

# Kiểm tra
redis-cli ping
```

## 2. Cấu hình Backend

### Tạo file .env
```bash
# Trong thư mục backend_python/
echo "REDIS_URL=redis://localhost:6379/0" > .env
```

### Cài đặt dependencies
```bash
cd backend_python
pip install -r requirements.txt
```

### Chạy backend
```bash
python run_server.py
```

## 3. Redis Insight Setup

### Tải Redis Insight
1. Truy cập: https://redis.com/redis-enterprise/redis-insight/
2. Tải phiên bản cho Windows
3. Cài đặt và chạy Redis Insight

### Kết nối Redis
1. Mở Redis Insight
2. Click "Add Redis Database"
3. Điền thông tin:
   - **Host**: `localhost`
   - **Port**: `6379`
   - **Database Alias**: `Apple Music Downloader`
   - **Username**: (để trống nếu không có auth)
   - **Password**: (để trống nếu không có auth)
4. Click "Add Redis Database"

## 4. Kiểm tra Redis Integration

### Test kết nối
```bash
# Test Redis CLI
redis-cli ping
# Kết quả: PONG

# Test từ Python
python -c "from backend_python.app.core.redis import is_redis_available; print('Redis available:', is_redis_available())"
```

### Tạo job test
1. Gửi POST request đến `http://localhost:8080/downloads`:
```json
{
  "url": "https://music.apple.com/us/album/test/123456789",
  "debug": true
}
```

2. Trong Redis Insight, bạn sẽ thấy:
   - **Hash**: `jobs:{job_id}` - thông tin job
   - **Hash**: `jobs:{job_id}:progress` - tiến độ download
   - **List**: `jobs:{job_id}:logs` - logs từ CLI

## 5. Redis Data Structure

### Job Storage (Hash)
```
Key: jobs:abc123def456
Fields:
- job_id: "abc123def456"
- args: "[\"--debug\", \"https://music.apple.com/...\"]"
- created_at: "1703123456.789"
- updated_at: "1703123456.789"
- status: "running"
- return_code: ""
```

### Progress Storage (Hash)
```
Key: jobs:abc123def456:progress
Fields:
- phase: "Downloading"
- percent: "73"
- speed: "20 MB/s"
- downloaded: "17/24 MB"
- total: "24 MB"
- updated_at: "1703123456.789"
```

### Logs Storage (List)
```
Key: jobs:abc123def456:logs
Values:
- "Track 1 of 5: Song Name"
- "Downloading... 73% (17/24 MB, 20 MB/s)"
- "Decrypting... 100%"
```

## 6. Monitoring & Debugging

### Redis Insight Features
- **Browser**: Xem tất cả keys, values
- **CLI**: Chạy Redis commands
- **Memory**: Theo dõi memory usage
- **Slow Log**: Xem slow queries

### Useful Commands
```bash
# Xem tất cả job keys
KEYS jobs:*

# Xem job details
HGETALL jobs:abc123def456

# Xem progress
HGETALL jobs:abc123def456:progress

# Xem logs (last 10 lines)
LRANGE jobs:abc123def456:logs -10 -1

# Xóa job cũ
DEL jobs:abc123def456 jobs:abc123def456:progress jobs:abc123def456:logs
```

## 7. Troubleshooting

### Redis không kết nối được
```bash
# Kiểm tra Redis đang chạy
docker ps | grep redis
# hoặc
redis-cli ping

# Kiểm tra port
netstat -an | grep 6379
```

### Backend fallback to in-memory
- Kiểm tra log: `Redis connection failed: ... Falling back to in-memory storage`
- Đảm bảo `REDIS_URL=redis://localhost:6379/0` trong .env
- Restart backend sau khi sửa .env

### Performance
- Redis keys có TTL 24h (86400 seconds)
- Logs giữ tối đa 5000 dòng
- Memory usage: ~1-5MB per job (tùy log size)
