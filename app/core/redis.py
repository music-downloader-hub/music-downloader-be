from __future__ import annotations

import json
import logging
from typing import Optional, Dict, Any, List
from redis import Redis
from redis.exceptions import ConnectionError, RedisError

from ..setting.setting import REDIS_URL, ENABLE_REDIS, CACHE_TTL_SECONDS, MAX_LOG_LINES

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[Redis] = None


def get_redis() -> Optional[Redis]:
    """Get Redis client instance with optimized connection pool. Returns None if Redis is not available."""
    global _redis_client
    if not ENABLE_REDIS:
        logger.info("Redis disabled in settings. Using in-memory storage.")
        return None
        
    if _redis_client is None and REDIS_URL:
        try:
            _redis_client = Redis.from_url(
                REDIS_URL, 
                decode_responses=True,
                max_connections=20,  # Connection pool
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            # Test connection
            _redis_client.ping()
            logger.info(f"Redis connected successfully to {REDIS_URL} with connection pooling")
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to in-memory storage.")
            _redis_client = None
    return _redis_client


def is_redis_available() -> bool:
    """Check if Redis is available and connected."""
    redis = get_redis()
    if redis is None:
        return False
    try:
        redis.ping()
        return True
    except (ConnectionError, RedisError):
        return False


class RedisJobStore:
    """Redis-based job storage with fallback to in-memory operations and performance optimizations."""
    
    def __init__(self):
        self.redis = get_redis()
        self.fallback_data: Dict[str, Dict[str, Any]] = {}
        # Local cache for batch operations
        self._log_buffer: Dict[str, List[str]] = {}
        self._progress_cache: Dict[str, Dict[str, Any]] = {}
        self._last_sync: Dict[str, float] = {}
    
    def _get_key(self, job_id: str, suffix: str = "") -> str:
        """Generate Redis key for job data."""
        return f"jobs:{job_id}{suffix}"
    
    def save_job(self, job_id: str, job_data: Dict[str, Any], ttl: int = None) -> bool:
        """Save job data to Redis or fallback storage."""
        key = self._get_key(job_id)
        try:
            if self.redis:
                # Convert non-serializable fields
                serializable_data = {k: v for k, v in job_data.items() 
                                   if k not in ['process', 'io_collector', 'sse_subscribers']}
                self.redis.hset(key, mapping=serializable_data)
                self.redis.expire(key, ttl or CACHE_TTL_SECONDS)
                return True
            else:
                # Fallback to in-memory
                self.fallback_data[key] = job_data.copy()
                return True
        except Exception as e:
            logger.error(f"Failed to save job {job_id}: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data from Redis or fallback storage."""
        key = self._get_key(job_id)
        try:
            if self.redis:
                data = self.redis.hgetall(key)
                if data:
                    # Convert string values back to appropriate types
                    if 'created_at' in data:
                        data['created_at'] = float(data['created_at'])
                    if 'updated_at' in data:
                        data['updated_at'] = float(data['updated_at'])
                    if 'return_code' in data and data['return_code']:
                        data['return_code'] = int(data['return_code'])
                    if 'args' in data:
                        data['args'] = json.loads(data['args'])
                return data if data else None
            else:
                return self.fallback_data.get(key)
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None
    
    def save_progress(self, job_id: str, progress_data: Dict[str, Any], ttl: int = None) -> bool:
        """Save job progress to Redis with local caching for performance."""
        import time
        
        # Cache progress locally
        self._progress_cache[job_id] = progress_data.copy()
        self._last_sync[job_id] = time.time()
        
        # Only sync to Redis if enough time has passed (throttle updates)
        if time.time() - self._last_sync.get(job_id, 0) < 0.5:  # 500ms throttle
            return True
            
        key = self._get_key(job_id, ":progress")
        try:
            if self.redis:
                # Use pipeline for batch operations
                pipe = self.redis.pipeline()
                pipe.hset(key, mapping=progress_data)
                pipe.expire(key, ttl or CACHE_TTL_SECONDS)
                pipe.execute()
                return True
            else:
                # Fallback to in-memory
                self.fallback_data[key] = progress_data.copy()
                return True
        except Exception as e:
            logger.error(f"Failed to save progress for job {job_id}: {e}")
            return False
    
    def get_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job progress from local cache or Redis."""
        # Try local cache first (faster)
        if job_id in self._progress_cache:
            return self._progress_cache[job_id]
            
        key = self._get_key(job_id, ":progress")
        try:
            if self.redis:
                data = self.redis.hgetall(key)
                if data and 'updated_at' in data:
                    data['updated_at'] = float(data['updated_at'])
                if data:
                    # Cache locally for next access
                    self._progress_cache[job_id] = data
                return data if data else None
            else:
                return self.fallback_data.get(key)
        except Exception as e:
            logger.error(f"Failed to get progress for job {job_id}: {e}")
            return None
    
    def append_log(self, job_id: str, log_line: str, max_lines: int = None) -> bool:
        """Append log line to Redis List with batch buffering for performance."""
        # Buffer logs locally first
        if job_id not in self._log_buffer:
            self._log_buffer[job_id] = []
        self._log_buffer[job_id].append(log_line)
        
        # Flush buffer when it gets large or periodically
        if len(self._log_buffer[job_id]) >= 10:  # Batch size
            return self._flush_log_buffer(job_id, max_lines)
        
        return True
    
    def _flush_log_buffer(self, job_id: str, max_lines: int = None) -> bool:
        """Flush buffered logs to Redis in batch."""
        if job_id not in self._log_buffer or not self._log_buffer[job_id]:
            return True
            
        key = self._get_key(job_id, ":logs")
        logs_to_flush = self._log_buffer[job_id].copy()
        self._log_buffer[job_id] = []  # Clear buffer
        
        try:
            if self.redis:
                # Batch operation: push all logs at once
                pipe = self.redis.pipeline()
                pipe.rpush(key, *logs_to_flush)
                pipe.ltrim(key, -(max_lines or MAX_LOG_LINES), -1)
                pipe.expire(key, CACHE_TTL_SECONDS)
                pipe.execute()
                return True
            else:
                # Fallback to in-memory
                if key not in self.fallback_data:
                    self.fallback_data[key] = []
                self.fallback_data[key].extend(logs_to_flush)
                # Keep only last N lines
                max_lines_actual = max_lines or MAX_LOG_LINES
                if len(self.fallback_data[key]) > max_lines_actual:
                    self.fallback_data[key] = self.fallback_data[key][-max_lines_actual:]
                return True
        except Exception as e:
            logger.error(f"Failed to flush logs for job {job_id}: {e}")
            return False
    
    def get_logs(self, job_id: str, last_n: Optional[int] = None) -> List[str]:
        """Get job logs from Redis List, including buffered logs."""
        # First flush any pending logs
        self._flush_log_buffer(job_id)
        
        key = self._get_key(job_id, ":logs")
        try:
            if self.redis:
                if last_n:
                    return self.redis.lrange(key, -last_n, -1)
                else:
                    return self.redis.lrange(key, 0, -1)
            else:
                # Fallback to in-memory
                logs = self.fallback_data.get(key, [])
                if last_n:
                    return logs[-last_n:] if last_n <= len(logs) else logs
                return logs
        except Exception as e:
            logger.error(f"Failed to get logs for job {job_id}: {e}")
            return []
    
    def delete_job(self, job_id: str) -> bool:
        """Delete job and all related data."""
        keys = [
            self._get_key(job_id),
            self._get_key(job_id, ":progress"),
            self._get_key(job_id, ":logs")
        ]
        try:
            if self.redis:
                # Use pipeline for batch delete
                pipe = self.redis.pipeline()
                pipe.delete(*keys)
                pipe.execute()
                return True
            else:
                # Fallback to in-memory
                for key in keys:
                    self.fallback_data.pop(key, None)
                return True
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            return False
    
    def flush_all_buffers(self) -> None:
        """Flush all pending buffers to Redis (useful for shutdown)."""
        for job_id in list(self._log_buffer.keys()):
            self._flush_log_buffer(job_id)
    
    def list_jobs(self) -> List[str]:
        """List all job IDs."""
        try:
            if self.redis:
                pattern = self._get_key("*")
                return [key.split(":", 1)[1] for key in self.redis.keys(pattern) 
                       if not key.endswith(":progress") and not key.endswith(":logs")]
            else:
                # Fallback to in-memory
                return [key.split(":", 1)[1] for key in self.fallback_data.keys() 
                       if key.startswith("jobs:") and not key.endswith(":progress") and not key.endswith(":logs")]
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []


# Global job store instance
job_store = RedisJobStore()
