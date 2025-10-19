from __future__ import annotations

import os
import shutil
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from ..core.redis import get_redis, is_redis_available
from ..setting.setting import (
    ENABLE_DISK_CACHE_MANAGEMENT,
    DISK_CACHE_TTL_SECONDS,
    DISK_CACHE_MAX_BYTES,
    DISK_CACHE_CLEANUP_INTERVAL,
    DISK_CACHE_LRU_EVICTION_THRESHOLD
)

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service for managing disk cache with TTL and LRU eviction.
    Implements Redis-based tracking of directory access times and sizes.
    """
    
    def __init__(self, downloads_root: Path):
        self.downloads_root = downloads_root
        self.redis = get_redis()
        self.enabled = ENABLE_DISK_CACHE_MANAGEMENT and is_redis_available()
        
        if not self.enabled:
            logger.info("Disk cache management disabled or Redis unavailable")
    
    def _get_dir_key(self, dir_path: str) -> str:
        """Generate Redis key for directory TTL tracking."""
        return f"dir:{dir_path}"
    
    def _get_lru_key(self) -> str:
        """Get Redis key for LRU tracking."""
        return "cache:lru"
    
    def _get_bytes_key(self) -> str:
        """Get Redis key for total cache bytes."""
        return "cache:bytes"
    
    def _get_lock_key(self, dir_path: str) -> str:
        """Get Redis key for directory lock during operations."""
        return f"lock:dir:{dir_path}"
    
    def _get_relative_path(self, full_path: Path) -> str:
        """Convert absolute path to relative path from downloads root."""
        try:
            return str(full_path.relative_to(self.downloads_root))
        except ValueError:
            # Path is not under downloads root
            return str(full_path)
    
    def _get_directory_size(self, dir_path: Path) -> int:
        """Calculate total size of directory in bytes."""
        total_size = 0
        try:
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to calculate size for {dir_path}: {e}")
        return total_size
    
    def register_directory(self, dir_path: Path) -> bool:
        """
        Register a directory in the cache system with TTL.
        Updates LRU tracking and size tracking.
        """
        if not self.enabled or not self.redis:
            return True
        
        try:
            # Validate that directory exists and is under downloads root
            if not dir_path.exists() or not dir_path.is_dir():
                logger.warning(f"Directory does not exist or is not a directory: {dir_path}")
                return False
            
            relative_path = self._get_relative_path(dir_path)
            if not relative_path or relative_path == ".":
                return True
            
            current_time = time.time()
            dir_size = self._get_directory_size(dir_path)
            
            # Set TTL for directory
            dir_key = self._get_dir_key(relative_path)
            self.redis.setex(dir_key, DISK_CACHE_TTL_SECONDS, str(current_time))
            
            # Update LRU tracking (ZSET with timestamp as score)
            lru_key = self._get_lru_key()
            self.redis.zadd(lru_key, {relative_path: current_time})
            
            # Update total cache size
            bytes_key = self._get_bytes_key()
            self.redis.incrby(bytes_key, dir_size)
            
            logger.debug(f"Registered directory {relative_path} with size {dir_size} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register directory {dir_path}: {e}")
            return False
    
    def touch_directory(self, dir_path: Path) -> bool:
        """
        Update last access time for a directory (LRU).
        Extends TTL if directory exists.
        """
        if not self.enabled or not self.redis:
            return True
        
        try:
            relative_path = self._get_relative_path(dir_path)
            if not relative_path or relative_path == ".":
                return True
            
            current_time = time.time()
            
            # Check if directory is tracked
            dir_key = self._get_dir_key(relative_path)
            if self.redis.exists(dir_key):
                # Extend TTL
                self.redis.expire(dir_key, DISK_CACHE_TTL_SECONDS)
                
                # Update LRU timestamp
                lru_key = self._get_lru_key()
                self.redis.zadd(lru_key, {relative_path: current_time})
                
                logger.debug(f"Touched directory {relative_path}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to touch directory {dir_path}: {e}")
        
        return False
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get current cache statistics."""
        if not self.enabled or not self.redis:
            return {"enabled": False}
        
        try:
            bytes_key = self._get_bytes_key()
            lru_key = self._get_lru_key()
            
            total_bytes = int(self.redis.get(bytes_key) or 0)
            total_dirs = self.redis.zcard(lru_key)
            
            return {
                "enabled": True,
                "total_bytes": total_bytes,
                "total_directories": total_dirs,
                "max_bytes": DISK_CACHE_MAX_BYTES,
                "usage_percent": (total_bytes / DISK_CACHE_MAX_BYTES * 100) if DISK_CACHE_MAX_BYTES > 0 else 0,
                "quota_exceeded": total_bytes > DISK_CACHE_MAX_BYTES if DISK_CACHE_MAX_BYTES > 0 else False
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"enabled": False, "error": str(e)}
    
    def cleanup_expired_directories(self) -> int:
        """
        Remove directories that have exceeded their TTL.
        Returns number of directories cleaned up.
        """
        if not self.enabled or not self.redis:
            return 0
        
        cleaned_count = 0
        try:
            # Find expired directories
            pattern = "dir:*"
            expired_dirs = []
            
            for key in self.redis.scan_iter(match=pattern):
                if not self.redis.exists(key):
                    # Key expired, extract directory path
                    dir_path = key.decode('utf-8').replace("dir:", "")
                    expired_dirs.append(dir_path)
            
            # Remove expired directories
            for dir_path in expired_dirs:
                if self._remove_directory_from_cache(dir_path):
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired directories")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired directories: {e}")
        
        return cleaned_count
    
    def enforce_quota(self) -> int:
        """
        Enforce cache quota by removing LRU directories.
        Returns number of directories removed.
        """
        if not self.enabled or not self.redis:
            return 0
        
        try:
            bytes_key = self._get_bytes_key()
            lru_key = self._get_lru_key()
            
            current_bytes = int(self.redis.get(bytes_key) or 0)
            
            if DISK_CACHE_MAX_BYTES <= 0 or current_bytes <= DISK_CACHE_MAX_BYTES * DISK_CACHE_LRU_EVICTION_THRESHOLD:
                return 0  # No eviction needed
            
            removed_count = 0
            target_bytes = DISK_CACHE_MAX_BYTES * 0.8  # Target 80% usage
            
            # Get directories sorted by access time (oldest first)
            directories = self.redis.zrange(lru_key, 0, -1, withscores=True)
            
            for dir_path_bytes, _ in directories:
                dir_path = dir_path_bytes.decode('utf-8')
                
                if current_bytes <= target_bytes:
                    break
                
                # Get directory size before removal
                full_path = self.downloads_root / dir_path
                dir_size = self._get_directory_size(full_path)
                
                if self._remove_directory_from_cache(dir_path, remove_files=True):
                    current_bytes -= dir_size
                    removed_count += 1
                    logger.info(f"Evicted directory {dir_path} ({dir_size} bytes)")
            
            logger.info(f"Quota enforcement removed {removed_count} directories")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to enforce quota: {e}")
            return 0
    
    def _remove_directory_from_cache(self, dir_path: str, remove_files: bool = False) -> bool:
        """
        Remove directory from cache tracking and optionally from disk.
        """
        if not self.enabled or not self.redis:
            return False
        
        try:
            # Acquire lock to prevent concurrent operations
            lock_key = self._get_lock_key(dir_path)
            if not self.redis.setnx(lock_key, "locked"):
                return False  # Directory is locked
            
            try:
                # Remove from Redis tracking
                dir_key = self._get_dir_key(dir_path)
                lru_key = self._get_lru_key()
                bytes_key = self._get_bytes_key()
                
                # Get directory size before removal
                full_path = self.downloads_root / dir_path
                dir_size = 0
                if full_path.exists():
                    dir_size = self._get_directory_size(full_path)
                
                # Remove from Redis
                self.redis.delete(dir_key)
                self.redis.zrem(lru_key, dir_path)
                self.redis.decrby(bytes_key, dir_size)
                
                # Remove from disk if requested
                if remove_files and full_path.exists():
                    shutil.rmtree(full_path, ignore_errors=True)
                    logger.info(f"Removed directory from disk: {dir_path}")
                
                logger.debug(f"Removed directory from cache: {dir_path}")
                return True
                
            finally:
                # Release lock
                self.redis.delete(lock_key)
                
        except Exception as e:
            logger.error(f"Failed to remove directory {dir_path}: {e}")
            return False
    
    def get_directory_info(self, dir_path: str) -> Optional[Dict[str, any]]:
        """Get information about a cached directory."""
        if not self.enabled or not self.redis:
            return None
        
        try:
            dir_key = self._get_dir_key(dir_path)
            lru_key = self._get_lru_key()
            
            # Get TTL info
            ttl = self.redis.ttl(dir_key)
            if ttl == -2:  # Key doesn't exist
                return None
            
            # Get LRU info
            score = self.redis.zscore(lru_key, dir_path)
            last_access = datetime.fromtimestamp(score) if score else None
            
            # Get directory size
            full_path = self.downloads_root / dir_path
            dir_size = self._get_directory_size(full_path) if full_path.exists() else 0
            
            return {
                "path": dir_path,
                "ttl_seconds": ttl if ttl > 0 else None,
                "last_access": last_access,
                "size_bytes": dir_size,
                "exists": full_path.exists()
            }
            
        except Exception as e:
            logger.error(f"Failed to get directory info for {dir_path}: {e}")
            return None
    
    def list_cached_directories(self, limit: int = 100) -> List[Dict[str, any]]:
        """List all cached directories with their info."""
        if not self.enabled or not self.redis:
            return []
        
        try:
            lru_key = self._get_lru_key()
            directories = self.redis.zrevrange(lru_key, 0, limit - 1, withscores=True)
            
            result = []
            for dir_path_bytes, score in directories:
                dir_path = dir_path_bytes.decode('utf-8')
                info = self.get_directory_info(dir_path)
                if info:
                    result.append(info)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list cached directories: {e}")
            return []
