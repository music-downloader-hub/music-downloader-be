# Redis Setup & Redis Insight Connection Guide

## 1. Cài đặt Redis

### Windows (Docker - Khuyến nghị)

#### Cài đặt Docker Desktop
1. Tải Docker Desktop từ: https://www.docker.com/products/docker-desktop/
2. Cài đặt và khởi động Docker Desktop
3. Đảm bảo Docker Engine đang chạy (biểu tượng Docker màu xanh)

#### Chạy Redis Container
```bash
# Chạy Redis container lần đầu
docker run -d --name redis-server -p 6379:6379 redis:7-alpine

# Kiểm tra Redis đang chạy
docker ps

# Nếu container đã tồn tại nhưng bị dừng
docker start redis-server

# Nếu muốn tạo container mới (xóa container cũ)
docker rm redis-server
docker run -d --name redis-server -p 6379:6379 redis:7-alpine
```

#### Quản lý Redis Container
```bash
# Xem tất cả container (bao gồm đã dừng)
docker ps -a

# Dừng Redis container
docker stop redis-server

# Khởi động lại Redis container
docker start redis-server

# Xóa Redis container
docker rm redis-server

# Xem logs Redis
docker logs redis-server

# Truy cập Redis CLI trong container
docker exec -it redis-server redis-cli
```

#### Test kết nối Redis
```bash
# Test từ host machine
redis-cli -h localhost -p 6379 ping
# Kết quả: PONG

# Test từ Python
python -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    result = r.ping()
    print(f'✅ Redis ping successful: {result}')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
"
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
   - **Host**: `localhost` (hoặc `127.0.0.1`)
   - **Port**: `6379`
   - **Database Alias**: `Apple Music Downloader`
   - **Username**: (để trống nếu không có auth)
   - **Password**: (để trống nếu không có auth)
4. Click "Add Redis Database"

### Kết nối Redis Docker Container
Nếu Redis chạy trong Docker container:
1. Đảm bảo container đang chạy: `docker ps`
2. Đảm bảo port mapping: `-p 6379:6379`
3. Sử dụng `localhost:6379` trong Redis Insight
4. Nếu không kết nối được, test: `docker exec -it redis-server redis-cli ping`

## 4. Kiểm tra Redis Integration

### Test kết nối
```bash
# Test Redis CLI (nếu cài đặt Redis CLI)
redis-cli ping
# Kết quả: PONG

# Test Redis CLI trong Docker container
docker exec -it redis-server redis-cli ping
# Kết quả: PONG

# Test từ Python
python -c "
from app.core.redis import is_redis_available
print('Redis available:', is_redis_available())
"

# Test kết nối Redis trực tiếp
python -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    result = r.ping()
    print(f'✅ Redis ping successful: {result}')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
"
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

### Redis Docker không kết nối được
```bash
# Kiểm tra Docker Desktop có chạy không
# Biểu tượng Docker trong system tray phải màu xanh

# Kiểm tra Redis container có chạy không
docker ps
# Phải thấy container redis-server với STATUS "Up"

# Nếu container không chạy
docker ps -a
# Xem container có tồn tại không, nếu có thì start lại
docker start redis-server

# Kiểm tra port 6379
netstat -an | findstr :6379
# Phải thấy :6379 LISTENING

# Test Redis CLI
docker exec -it redis-server redis-cli ping
# Kết quả: PONG
```

### Redis không kết nối được (tổng quát)
```bash
# Kiểm tra Redis đang chạy
docker ps | grep redis
# hoặc
redis-cli ping

# Kiểm tra port
netstat -an | findstr :6379
```

### Docker Desktop Issues
```bash
# Nếu Docker Desktop không khởi động được
# 1. Restart Docker Desktop
# 2. Kiểm tra WSL2 (Windows Subsystem for Linux) có được cài đặt không
# 3. Kiểm tra Hyper-V có được enable không

# Kiểm tra Docker daemon
docker version
# Phải thấy cả Client và Server version

# Reset Docker Desktop (nếu cần)
# Settings > Reset to factory defaults
```

### Backend fallback to in-memory
- Kiểm tra log: `Redis connection failed: ... Falling back to in-memory storage`
- Đảm bảo `REDIS_URL=redis://localhost:6379/0` trong .env
- Restart backend sau khi sửa .env

### Performance
- Redis keys có TTL 24h (86400 seconds)
- Logs giữ tối đa 5000 dòng
- Memory usage: ~1-5MB per job (tùy log size)
