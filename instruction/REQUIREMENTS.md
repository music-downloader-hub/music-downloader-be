# Yêu cầu hệ thống và Dependencies

## 📋 Tổng quan

Tài liệu này liệt kê tất cả các yêu cầu hệ thống, thư viện, framework và công cụ cần thiết để Apple Music Downloader Backend hoạt động đầy đủ.

## 🖥️ Yêu cầu hệ thống

### Hệ điều hành
- **Windows 10/11** (khuyến nghị)
- **macOS 10.15+**
- **Linux Ubuntu 18.04+**

### Phần cứng tối thiểu
- **RAM**: 4GB (khuyến nghị 8GB+)
- **Ổ cứng**: 10GB trống
- **CPU**: 2 cores (khuyến nghị 4 cores+)

## 🐍 Python Backend

### Python Version
```bash
Python 3.8+ (khuyến nghị Python 3.10+)
```

### Virtual Environment
```bash
# Tạo virtual environment
python -m venv .venv

# Kích hoạt (Windows)
.venv\Scripts\activate

# Kích hoạt (macOS/Linux)
source .venv/bin/activate
```

### Python Dependencies
```bash
# Cài đặt từ requirements.txt
pip install -r requirements.txt
```

#### Core Dependencies
```
fastapi==0.104.1          # Web framework
uvicorn[standard]==0.24.0  # ASGI server
pydantic==2.5.0           # Data validation
python-dotenv==1.0.0      # Environment variables
```

#### Redis Integration
```
redis==5.0.1              # Redis client
redis-py-cluster==2.1.3   # Redis cluster support
```

#### HTTP & Networking
```
httpx==0.25.2             # HTTP client
aiofiles==23.2.1          # Async file operations
```

#### Utilities
```
pathlib2==2.3.7           # Path utilities
typing-extensions==4.8.0  # Type hints
```

#### Development Dependencies
```
pytest==7.4.3            # Testing framework
pytest-asyncio==0.21.1   # Async testing
black==23.11.0            # Code formatter
flake8==6.1.0             # Linting
```

## 🐳 Docker & Redis

### Docker Desktop
```bash
# Tải và cài đặt Docker Desktop
# Windows: https://www.docker.com/products/docker-desktop/
# macOS: https://www.docker.com/products/docker-desktop/
# Linux: https://docs.docker.com/engine/install/
```

### Redis Options

#### Option 1: Local Redis (Docker)
```bash
# Chạy Redis container
docker run -d --name redis-server -p 6379:6379 redis:7-alpine

# Kiểm tra Redis đang chạy
docker ps

# Test kết nối Redis
docker exec -it redis-server redis-cli ping
# Kết quả: PONG
```

#### Option 2: Redis Cloud (Khuyến nghị cho Production)
```bash
# Cách 1: Sử dụng script tự động
cd backend/scripts
python switch_redis_mode.py cloud

# Cách 2: Sửa thủ công trong setting.py
# REDIS_MODE = "cloud"  # Chuyển từ "localhost" sang "cloud"

# Thông tin Redis Cloud hiện tại:
# Host: redis-18425.c295.ap-southeast-1-1.ec2.redns.redis-cloud.com
# Port: 18425
# Password: os.getenv("REDIS_CLOUD_PASSWORD")

# Test kết nối Redis Cloud
redis-cli -h redis-18425.c295.ap-southeast-1-1.ec2.redns.redis-cloud.com -p 18425 -a {os.getenv("REDIS_CLOUD_PASSWORD")} ping
# Kết quả: PONG

# Test bằng Python script
cd backend/test
python test_redis_cloud.py
```

### Redis Management Tools
```bash
# RedisInsight (GUI tool)
# Tải từ: https://redis.com/redis-enterprise/redis-insight/
# Kết nối: localhost:6379 (local) hoặc your-redis-host:port (cloud)
```

## 🔧 Go Module (Downloader)

### Go Version
```bash
Go 1.19+ (khuyến nghị Go 1.21+)
```

### Go Dependencies
```bash
# Vào thư mục Go module
cd backend/modules/downloaders

# Tải dependencies
go mod tidy
go mod download
```

#### Core Go Dependencies
```go
// go.mod
module apple-music-downloader

go 1.21

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/go-resty/resty/v2 v2.10.0
    github.com/sirupsen/logrus v1.9.3
    github.com/spf13/cobra v1.8.0
    github.com/spf13/viper v1.17.0
)
```

#### Apple Music API
```go
// utils/ampapi/
github.com/go-resty/resty/v2 v2.10.0  // HTTP client
github.com/tidwall/gjson v1.17.0      // JSON parsing
```

#### Audio Processing
```go
// utils/runv3/
github.com/hajimehoshi/go-mp3 v0.3.4  // MP3 processing
github.com/tosone/minimp3 v1.0.2      // MP3 decoder
```

#### Task Management
```go
// utils/task/
github.com/robfig/cron/v3 v3.0.1      // Cron jobs
github.com/go-co-op/gocron v1.35.0    // Job scheduler
```

### External Tools (Bắt buộc)

#### MP4Box (GPAC)
```bash
# Windows
# Tải từ: https://gpac.io/downloads/gpac-nightly-builds/
# Cài đặt và thêm vào PATH environment variables

# macOS (Homebrew)
brew install gpac

# Linux (Ubuntu/Debian)
sudo apt-get install gpac

# Kiểm tra cài đặt
MP4Box -version
```

#### MP4Decrypt (Bento4)
```bash
# Windows
# Tải từ: https://www.bento4.com/downloads/
# Giải nén và thêm vào PATH

# macOS (Homebrew)
brew install bento4

# Linux
# Tải từ: https://www.bento4.com/downloads/
# Giải nén và thêm vào PATH

# Kiểm tra cài đặt
mp4decrypt --version
```

#### FFmpeg (Tùy chọn)
```bash
# Windows
# Tải từ: https://ffmpeg.org/download.html
# Hoặc dùng chocolatey: choco install ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt-get install ffmpeg

# Kiểm tra cài đặt
ffmpeg -version
```

### Apple Music Configuration

#### Media User Token
```bash
# Cần thiết cho:
# - AAC-LC downloads
# - MV downloads  
# - Lyrics downloads

# Cách lấy:
# 1. Mở Apple Music (https://music.apple.com) và đăng nhập
# 2. Mở Developer Tools (F12)
# 3. Application -> Storage -> Cookies -> https://music.apple.com
# 4. Tìm cookie "media-user-token" và copy value
# 5. Paste vào config.yaml
```

#### Supported Audio Formats
```
- alac (audio-alac-stereo)     # Lossless
- ec3 (audio-atmos / audio-ec3) # Dolby Atmos
- aac (audio-stereo)           # Standard AAC
- aac-lc (audio-stereo)        # AAC-LC (cần media-user-token)
- aac-binaural (audio-stereo-binaural)
- aac-downmix (audio-stereo-downmix)
- MV (Music Video)             # Cần media-user-token
```

## 🐳 Docker Wrapper

### Docker Requirements
```bash
# Docker Desktop đã cài đặt (như trên)
# Docker Engine version 20.10+
```

### Wrapper Dependencies
```dockerfile
# backend/modules/wrapper/Dockerfile
FROM alpine:3.18

# Cài đặt dependencies
RUN apk add --no-cache \
    curl \
    wget \
    ca-certificates \
    tzdata

# Copy wrapper binary
COPY wrapper /usr/local/bin/
COPY rootfs/ /app/rootfs/

# Expose port
EXPOSE 10020

# Run wrapper
CMD ["wrapper"]
```

### Wrapper Source (C)
```c
// backend/modules/wrapper/main.c
// Dependencies: libc, pthread, curl
// Compile với: gcc -o wrapper main.c -lcurl -lpthread
```

### Wrapper Installation & Usage

#### Docker Method (Khuyến nghị cho Windows)
```bash
# 1. Build Docker image
cd backend/modules/wrapper
docker build --tag wrapper .

# 2. Tạo thư mục cần thiết
mkdir -p rootfs/data/data/com.apple.android.music/files

# 3. Chạy với Apple Music login
docker run -v ./rootfs/data:/app/rootfs/data -p 10020:10020 \
  -e args="-L username:password -F -H 0.0.0.0" wrapper

# 4. Chạy không login (nếu đã login trước đó)
docker run -v ./rootfs/data:/app/rootfs/data -p 10020:10020 \
  -e args="-H 0.0.0.0" wrapper

# 5. Kiểm tra container
docker ps

# 6. Xem logs
docker logs wrapper-service

# 7. Dừng service
docker stop wrapper-service
docker rm wrapper-service
```

#### Native Installation (Linux x86_64/arm64)
```bash
# x86_64
sudo -i
wget "https://github.com/zhaarey/wrapper/releases/download/linux.V2/wrapper.x86_64.tar.gz"
mkdir wrapper
tar -xzf wrapper.x86_64.tar.gz -C wrapper
cd wrapper
./wrapper

# arm64
sudo -i
wget "https://github.com/zhaarey/wrapper/releases/download/arm64/wrapper.arm64.tar.gz"
mkdir wrapper
tar -xzf wrapper.arm64.tar.gz -C wrapper
cd wrapper
./wrapper
```

#### Wrapper Command Options
```bash
./wrapper [OPTION]...
  -h, --help               Print help and exit
  -V, --version            Print version and exit
  -H, --host=STRING        (default: 127.0.0.1)
  -D, --decrypt-port=INT   (default: 10020)
  -M, --m3u8-port=INT      (default: 20020)
  -P, --proxy=STRING       (default: '')
  -L, --login=STRING       ([username] [password])
```

### Wrapper Environment Requirements
```bash
# Hỗ trợ:
# - Linux x86_64 và arm64
# - Windows Subsystem for Linux (WSL) - khuyến nghị
# - Docker Desktop (Windows) - đã được modify để hỗ trợ

# Không cần Android emulator để decrypt ALAC files
# Tất cả files từ anonymous source
```

## 🌐 Frontend Dependencies

### Node.js
```bash
Node.js 16+ (khuyến nghị Node.js 18+)
npm 8+ hoặc yarn 1.22+
```

### React Dependencies
```bash
# Vào thư mục frontend
cd frontend

# Cài đặt dependencies
npm install
```

#### Core Frontend Dependencies
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0",
    "react-router-dom": "^6.8.0",
    "antd": "^5.12.0",
    "dayjs": "^1.11.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "eslint": "^8.0.0"
  }
}
```

## 🔧 Development Tools

### Code Editor
- **Visual Studio Code** (khuyến nghị)
- **PyCharm** (cho Python)
- **GoLand** (cho Go)

### VS Code Extensions
```json
{
  "recommendations": [
    "ms-python.python",
    "golang.go",
    "ms-vscode.vscode-typescript-next",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-json"
  ]
}
```

### Git
```bash
Git 2.30+ (khuyến nghị Git 2.40+)
```

## 📦 Package Managers

### Python
```bash
pip 21.0+ (khuyến nghị pip 23.0+)
```

### Go
```bash
go mod (built-in với Go 1.11+)
```

### Node.js
```bash
npm 8+ hoặc yarn 1.22+
```

### Docker
```bash
Docker Desktop 4.0+
Docker Compose 2.0+
```

## 🧹 Cache Management System

### Background Cleaner Service
- **Tự động dọn dẹp**: Chạy định kỳ mỗi 30 phút
- **TTL-based cleanup**: Xóa thư mục hết hạn TTL
- **Lock mechanism**: Tránh xung đột khi xóa

### Cache Settings
```python
# TTL cho thư mục cache
DISK_CACHE_TTL_SECONDS = 86400  # 24 giờ

# Quota tối đa cho cache
DISK_CACHE_MAX_BYTES = 10 * 1024 * 1024 * 1024  # 10GB

# Tần suất chạy cleaner
DISK_CACHE_CLEANUP_INTERVAL = 1800  # 30 phút

# Ngưỡng bắt đầu xóa LRU
DISK_CACHE_LRU_EVICTION_THRESHOLD = 0.9  # 90%

```

### API Endpoints
```
GET  /cleaner/stats     - Thống kê cleaner service
POST /cleaner/run       - Chạy cleanup ngay lập tức
GET  /cleaner/status    - Trạng thái scheduler
POST /cleaner/start     - Start scheduler
POST /cleaner/stop      - Stop scheduler
```

## 🔐 Environment Variables

### Tạo file .env
```bash
# Tạo file .env trong thư mục backend/
cd backend
touch .env  # Linux/macOS
# hoặc tạo file .env bằng text editor trên Windows
```

### Load .env file
```bash
# Backend tự động load .env file khi chạy run_server.py
# Không cần cấu hình thêm
```

### Backend (.env)
```bash
# Server Configuration
HOST=localhost
PORT=8080
RELOAD=true

# Redis Configuration (Local)
REDIS_URL=redis://localhost:6379/0
ENABLE_REDIS=true

# Redis Configuration (Cloud) - Bắt buộc phải có trong .env
REDIS_CLOUD_PASSWORD=your_redis_cloud_password_here

# - File .env chứa thông tin nhạy cảm
# - KHÔNG commit file .env vào Git
# - File .env đã được thêm vào .gitignore
# - Chỉ lưu password trong .env, KHÔNG lưu trong setting.py

# Troubleshooting .env file
# Nếu gặp lỗi "Authentication required" với Redis Cloud:
# 1. Kiểm tra file .env có đúng vị trí: backend/.env
# 2. Kiểm tra format: REDIS_CLOUD_PASSWORD=your_password (không có dấu cách)
# 3. Chạy test: python test_env.py
# 4. Restart server sau khi sửa .env

# Wrapper Configuration
WRAPPER_USERNAME=your_username
WRAPPER_PASSWORD=your_password
WRAPPER_ARGS=additional_args

# Feature Flags
ENABLE_DEDUPLICATION=true
ENABLE_DISK_CACHE_MANAGEMENT=true
ENABLE_SPOTIFY=false

# Cache Management Settings
DISK_CACHE_TTL_SECONDS=86400
DISK_CACHE_MAX_BYTES=10737418240
DISK_CACHE_CLEANUP_INTERVAL=1800
DISK_CACHE_LRU_EVICTION_THRESHOLD=0.9

```

### Frontend (.env)
```bash
VITE_API_BASE_URL=http://localhost:8080
VITE_APP_TITLE=Apple Music Downloader
```

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd apple-music-downloader
```

### 2. Setup Backend
```bash
# Tạo virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Cài đặt Python dependencies
cd backend
pip install -r requirements.txt
```

### 3. Setup Redis
```bash
# Option 1: Local Redis (Docker)
docker run -d --name redis-server -p 6379:6379 redis:7-alpine
docker exec -it redis-server redis-cli ping

# Option 2: Redis Cloud (Production)
# Chỉ cần cập nhật setting.py:
# REDIS_MODE = "cloud"
# Không cần cài đặt gì thêm
```

### 4. Setup External Tools
```bash
# Cài đặt MP4Box (GPAC)
# Windows: Tải từ https://gpac.io/downloads/gpac-nightly-builds/
# macOS: brew install gpac
# Linux: sudo apt-get install gpac

# Cài đặt MP4Decrypt (Bento4)
# Windows: Tải từ https://www.bento4.com/downloads/
# macOS: brew install bento4
# Linux: Tải từ https://www.bento4.com/downloads/

# Kiểm tra cài đặt
MP4Box -version
mp4decrypt --version
```

### 5. Setup Go Module
```bash
cd backend/modules/downloaders
go mod tidy
go mod download
```

### 6. Setup Wrapper
```bash
cd backend/modules/wrapper
docker build -t wrapper .

# Tạo thư mục cần thiết
mkdir -p rootfs/data/data/com.apple.android.music/files
```

### 7. Setup Frontend
```bash
cd frontend
npm install
```

### 8. Run Application
```bash
# Terminal 1: Backend
cd backend
python run_server.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

## 🔍 Verification

### Check Backend
```bash
curl http://localhost:8080/health
# Kết quả: {"status": "healthy"}
```

### Check Redis
```bash
docker exec -it redis-server redis-cli ping
# Kết quả: PONG
```

### Check Frontend
```bash
# Mở browser: http://localhost:3000
# Kiểm tra giao diện load thành công
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Redis Connection Failed
```bash
# Local Redis
# Kiểm tra Docker Desktop đang chạy
# Kiểm tra Redis container
docker ps | grep redis

# Restart Redis container
docker restart redis-server

# Redis Cloud
# Kiểm tra kết nối mạng
ping redis-18425.c295.ap-southeast-1-1.ec2.redns.redis-cloud.com

# Test kết nối Redis Cloud
redis-cli -h redis-18425.c295.ap-southeast-1-1.ec2.redns.redis-cloud.com -p 18425 -a hu8fSwozwhIjHMTfDs7bz6UYtrt4Ct8e ping

# Kiểm tra firewall/security groups
# Đảm bảo port 18425 được mở
```

#### 2. Python Dependencies Error
```bash
# Cập nhật pip
pip install --upgrade pip

# Cài đặt lại dependencies
pip install -r requirements.txt --force-reinstall
```

#### 3. Go Module Error
```bash
# Clean module cache
go clean -modcache

# Tải lại dependencies
go mod tidy
go mod download
```

#### 4. Docker Build Error
```bash
# Clean Docker cache
docker system prune -a

# Rebuild wrapper
cd backend/modules/wrapper
docker build -t wrapper . --no-cache
```

#### 5. MP4Box Not Found
```bash
# Windows: Kiểm tra PATH environment variable
echo $env:PATH

# Thêm GPAC vào PATH
# Vào System Properties -> Environment Variables
# Thêm đường dẫn GPAC vào PATH

# Test lại
MP4Box -version
```

#### 6. MP4Decrypt Not Found
```bash
# Windows: Kiểm tra PATH environment variable
echo $env:PATH

# Thêm Bento4 vào PATH
# Copy mp4decrypt.exe vào thư mục trong PATH
# Hoặc thêm đường dẫn Bento4 vào PATH

# Test lại
mp4decrypt --version
```

#### 7. Wrapper Connection Failed
```bash
# Kiểm tra wrapper container
docker ps | grep wrapper

# Kiểm tra port 10020
netstat -an | findstr :10020

# Restart wrapper
docker stop wrapper-service
docker rm wrapper-service
cd backend/modules/wrapper
docker run -v ./rootfs/data:/app/rootfs/data -p 10020:10020 \
  -e args="-H 0.0.0.0" wrapper
```

#### 8. Apple Music Token Issues
```bash
# Kiểm tra media-user-token trong config.yaml
# Đảm bảo token còn hiệu lực
# Lấy token mới từ Apple Music website
# Cập nhật config.yaml và restart Go module
```

## 📚 Additional Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Redis Documentation](https://redis.io/docs/)
- [Go Documentation](https://golang.org/doc/)
- [Docker Documentation](https://docs.docker.com/)

### Community
- [FastAPI GitHub](https://github.com/tiangolo/fastapi)
- [Redis GitHub](https://github.com/redis/redis)
- [Go GitHub](https://github.com/golang/go)

---

**Lưu ý**: Đảm bảo tất cả dependencies được cài đặt đúng version để tránh conflict và lỗi runtime.
