from __future__ import annotations
import os

# Redis Configuration Mode
REDIS_MODE = "cloud"

# Local Redis Configuration
REDIS_LOCAL_URL = "redis://localhost:6379/0"
REDIS_LOCAL_HOST = "localhost"
REDIS_LOCAL_PORT = 6379
REDIS_LOCAL_DB = 0
REDIS_LOCAL_PASSWORD = None

# Cloud Redis Configuration
REDIS_CLOUD_URL = "redis://redis-18425.c295.ap-southeast-1-1.ec2.redns.redis-cloud.com:18425/0"
REDIS_CLOUD_HOST = "redis-18425.c295.ap-southeast-1-1.ec2.redns.redis-cloud.com"
REDIS_CLOUD_PORT = 18425
REDIS_CLOUD_DB = 0
REDIS_CLOUD_PASSWORD = os.getenv("REDIS_CLOUD_PASSWORD")

# Dynamic Redis Configuration (based on mode)
def get_redis_config():
    if REDIS_MODE == "cloud":
        return {
            "url": REDIS_CLOUD_URL,
            "host": REDIS_CLOUD_HOST,
            "port": REDIS_CLOUD_PORT,
            "db": REDIS_CLOUD_DB,
            "password": REDIS_CLOUD_PASSWORD
        }
    else:  # localhost
        return {
            "url": REDIS_LOCAL_URL,
            "host": REDIS_LOCAL_HOST,
            "port": REDIS_LOCAL_PORT,
            "db": REDIS_LOCAL_DB,
            "password": REDIS_LOCAL_PASSWORD
        }

# Current Redis Configuration
redis_config = get_redis_config()
REDIS_URL = redis_config["url"]
REDIS_HOST = redis_config["host"]
REDIS_PORT = redis_config["port"]
REDIS_DB = redis_config["db"]
REDIS_PASSWORD = redis_config["password"]
# Cache Configuration
CACHE_TTL_SECONDS = 86400  # 24 hours
CACHE_MAX_BYTES = 0  # 0 = unlimited

# Disk Cache Management
ENABLE_DISK_CACHE_MANAGEMENT = True  # Enable disk cache TTL + quota management
DISK_CACHE_TTL_SECONDS = 86400  # 24 hours TTL for directories
DISK_CACHE_MAX_BYTES = 10 * 1024 * 1024 * 1024  # 10GB default quota
DISK_CACHE_LRU_EVICTION_THRESHOLD = 0.9  # Start eviction at 90% quota

# Cleaner Configuration
DISK_CACHE_CLEANUP_INTERVAL = 3600  # 1 hour cleanup interval (how often to run cleaner)

# Feature Flags
ENABLE_SPOTIFY = False
ENABLE_REDIS = True  # Set to False to force in-memory mode
ENABLE_REDIS_LOGS = False  # Disable Redis logging during download for performance
ENABLE_REDIS_PROGRESS = True  # Disable Redis progress updates for maximum performance

# Performance Testing
ENABLE_PERFORMANCE_LOGGING = False  # Log performance metrics

# Deduplication
ENABLE_DEDUPLICATION = True  # Enable duplicate request prevention
DEDUPE_LOCK_TTL = 3600  # 1 hour lock TTL

# Job Configuration
MAX_LOG_LINES = 5000
JOB_TTL_SECONDS = 86400  # 24 hours

# Server Configuration
HOST = "localhost"
PORT = 8080
RELOAD = True