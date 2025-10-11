from __future__ import annotations

# Redis Configuration
REDIS_URL = "redis://localhost:6379/0"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None  # Set to password string if needed

# Cache Configuration
CACHE_TTL_SECONDS = 86400  # 24 hours
CACHE_MAX_BYTES = 0  # 0 = unlimited

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