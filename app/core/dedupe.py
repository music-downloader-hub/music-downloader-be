from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional, Dict, Any

from .redis import get_redis, is_redis_available
from ..setting.setting import ENABLE_DEDUPLICATION, DEDUPE_LOCK_TTL

logger = logging.getLogger(__name__)


class DedupeService:
    """Service for preventing duplicate download requests using Redis locks."""
    
    def __init__(self):
        self.redis = get_redis()
        self.enabled = ENABLE_DEDUPLICATION and is_redis_available()
    
    def _generate_content_key(self, url: str, options: Dict[str, Any]) -> str:
        """Generate a unique content key from URL and download options."""
        # Create a deterministic key from URL and options
        key_data = {
            "url": url,
            "song": options.get("song", False),
            "atmos": options.get("atmos", False),
            "aac": options.get("aac", False),
            "select": options.get("select", False),
            "all_album": options.get("all_album", False),
            "debug": options.get("debug", False),
            "search_type": options.get("search_type"),
            "search_term": options.get("search_term"),
        }
        
        # Remove None values and sort for consistency
        key_data = {k: v for k, v in key_data.items() if v is not None}
        key_string = json.dumps(key_data, sort_keys=True)
        
        # Create hash for shorter key
        content_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"content:{content_hash}"
    
    def _get_lock_key(self, content_key: str) -> str:
        """Get Redis lock key for content."""
        return f"lock:{content_key}"
    
    def _get_job_key(self, content_key: str) -> str:
        """Get Redis key for content to job mapping."""
        return f"job:{content_key}"
    
    def acquire_lock(self, content_key: str, job_id: str) -> bool:
        """Acquire lock for content key. Returns True if successful."""
        if not self.enabled:
            return True
            
        lock_key = self._get_lock_key(content_key)
        job_key = self._get_job_key(content_key)
        
        try:
            # Try to set lock with TTL
            if self.redis.setnx(lock_key, job_id):
                # Set TTL for lock
                self.redis.expire(lock_key, DEDUPE_LOCK_TTL)
                # Map content to job
                self.redis.setex(job_key, DEDUPE_LOCK_TTL, job_id)
                logger.info(f"Acquired lock for content {content_key} -> job {job_id}")
                return True
            else:
                logger.info(f"Lock already exists for content {content_key}")
                return False
        except Exception as e:
            logger.error(f"Failed to acquire lock for {content_key}: {e}")
            return False
    
    def get_existing_job(self, content_key: str) -> Optional[str]:
        """Get existing job ID for content key if lock exists."""
        if not self.enabled:
            return None
            
        job_key = self._get_job_key(content_key)
        
        try:
            job_id = self.redis.get(job_key)
            if job_id:
                logger.info(f"Found existing job {job_id} for content {content_key}")
                return job_id
            return None
        except Exception as e:
            logger.error(f"Failed to get existing job for {content_key}: {e}")
            return None
    
    def release_lock(self, content_key: str, job_id: str) -> bool:
        """Release lock for content key."""
        if not self.enabled:
            return True
            
        lock_key = self._get_lock_key(content_key)
        job_key = self._get_job_key(content_key)
        
        try:
            # Use Lua script for atomic check and delete
            lua_script = """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                redis.call("DEL", KEYS[1])
                redis.call("DEL", KEYS[2])
                return 1
            else
                return 0
            end
            """
            
            result = self.redis.eval(lua_script, 2, lock_key, job_key, job_id)
            if result:
                logger.info(f"Released lock for content {content_key} -> job {job_id}")
                return True
            else:
                logger.warning(f"Lock not owned by job {job_id} for content {content_key}")
                return False
        except Exception as e:
            logger.error(f"Failed to release lock for {content_key}: {e}")
            return False
    
    def is_locked(self, content_key: str) -> bool:
        """Check if content key is currently locked."""
        if not self.enabled:
            return False
            
        lock_key = self._get_lock_key(content_key)
        
        try:
            return bool(self.redis.exists(lock_key))
        except Exception as e:
            logger.error(f"Failed to check lock status for {content_key}: {e}")
            return False
    
    def cleanup_expired_locks(self) -> int:
        """Clean up expired locks (called periodically)."""
        if not self.enabled:
            return 0
            
        try:
            # Get all lock keys
            lock_keys = self.redis.keys("lock:content:*")
            cleaned = 0
            
            for lock_key in lock_keys:
                # Check if lock has TTL (expired locks have no TTL)
                ttl = self.redis.ttl(lock_key)
                if ttl == -1:  # No TTL set, should be cleaned
                    content_key = lock_key.replace("lock:", "")
                    job_key = self._get_job_key(content_key)
                    
                    # Remove both lock and job mapping
                    self.redis.delete(lock_key, job_key)
                    cleaned += 1
                    logger.info(f"Cleaned up expired lock for {content_key}")
            
            return cleaned
        except Exception as e:
            logger.error(f"Failed to cleanup expired locks: {e}")
            return 0


# Global instance
dedupe_service = DedupeService()
