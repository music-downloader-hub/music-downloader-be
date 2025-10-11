from __future__ import annotations

import os
import shutil
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional

from ..core.redis import get_redis, is_redis_available
from ..setting.setting import (
    ENABLE_DISK_CACHE_MANAGEMENT,
    DISK_CACHE_CLEANUP_INTERVAL,
    PERMANENT_SAVE,
    PERMANENT_SAVE_DIR
)

logger = logging.getLogger(__name__)


class CleanerService:
    """
    Background service for cleaning expired directories from AM-DL downloads.
    Implements TTL-based cleanup with Redis tracking and lock mechanism.
    """
    
    def __init__(self, downloads_root: Path):
        self.downloads_root = downloads_root
        self.redis = get_redis()
        self.enabled = ENABLE_DISK_CACHE_MANAGEMENT and is_redis_available()
        
        if not self.enabled:
            logger.info("Disk cache management disabled or Redis unavailable - cleaner disabled")
    
    def _get_dir_key(self, dir_path: str) -> str:
        """Generate Redis key for directory TTL tracking."""
        return f"dir:{dir_path}"
    
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
    
    def _is_directory_expired(self, dir_path: Path) -> bool:
        """Check if directory has expired TTL in Redis."""
        if not self.enabled or not self.redis:
            return False
        
        try:
            relative_path = self._get_relative_path(dir_path)
            if not relative_path or relative_path == ".":
                return False
            
            dir_key = self._get_dir_key(relative_path)
            return not self.redis.exists(dir_key)
        except Exception as e:
            logger.error(f"Failed to check TTL for {dir_path}: {e}")
            return False
    
    def _is_directory_locked(self, dir_path: Path) -> bool:
        """Check if directory is currently locked for operations."""
        if not self.enabled or not self.redis:
            return False
        
        try:
            relative_path = self._get_relative_path(dir_path)
            if not relative_path or relative_path == ".":
                return False
            
            lock_key = self._get_lock_key(relative_path)
            return self.redis.exists(lock_key)
        except Exception as e:
            logger.error(f"Failed to check lock for {dir_path}: {e}")
            return False
    
    def _lock_directory(self, dir_path: Path) -> bool:
        """Lock directory for cleanup operations."""
        if not self.enabled or not self.redis:
            return False
        
        try:
            relative_path = self._get_relative_path(dir_path)
            if not relative_path or relative_path == ".":
                return False
            
            lock_key = self._get_lock_key(relative_path)
            # Use SETNX to atomically set lock if not exists
            return self.redis.setnx(lock_key, "cleaning")
        except Exception as e:
            logger.error(f"Failed to lock directory {dir_path}: {e}")
            return False
    
    def _unlock_directory(self, dir_path: Path) -> bool:
        """Unlock directory after cleanup operations."""
        if not self.enabled or not self.redis:
            return False
        
        try:
            relative_path = self._get_relative_path(dir_path)
            if not relative_path or relative_path == ".":
                return False
            
            lock_key = self._get_lock_key(relative_path)
            return self.redis.delete(lock_key) > 0
        except Exception as e:
            logger.error(f"Failed to unlock directory {dir_path}: {e}")
            return False
    
    def _copy_to_permanent_storage(self, source_dir: Path) -> bool:
        """Copy directory to permanent storage if enabled."""
        if not PERMANENT_SAVE or not PERMANENT_SAVE_DIR:
            return True  # Not enabled, consider success
        
        try:
            permanent_dir = Path(PERMANENT_SAVE_DIR)
            permanent_dir.mkdir(parents=True, exist_ok=True)
            
            # Get relative path from downloads root
            relative_path = self._get_relative_path(source_dir)
            if not relative_path or relative_path == ".":
                return True
            
            # Create destination path in permanent storage
            dest_dir = permanent_dir / relative_path
            
            # Skip if already exists
            if dest_dir.exists():
                logger.debug(f"Permanent copy already exists: {dest_dir}")
                return True
            
            # Copy directory
            shutil.copytree(source_dir, dest_dir)
            logger.info(f"Copied to permanent storage: {source_dir} -> {dest_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy to permanent storage {source_dir}: {e}")
            return False
    
    def _remove_directory(self, dir_path: Path) -> bool:
        """Safely remove directory from disk."""
        try:
            if dir_path.exists() and dir_path.is_dir():
                shutil.rmtree(dir_path, ignore_errors=True)
                logger.info(f"Removed expired directory: {dir_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove directory {dir_path}: {e}")
            return False
    
    def scan_and_cleanup(self) -> Dict[str, int]:
        """
        Scan AM-DL downloads directory and clean up expired directories.
        Returns statistics about cleanup operation.
        """
        stats = {
            "scanned": 0,
            "expired": 0,
            "locked": 0,
            "copied": 0,
            "removed": 0,
            "errors": 0
        }
        
        if not self.enabled:
            logger.info("Cleaner service disabled")
            return stats
        
        if not self.downloads_root.exists():
            logger.warning(f"Downloads root does not exist: {self.downloads_root}")
            return stats
        
        logger.info(f"Starting cleanup scan of {self.downloads_root}")
        
        try:
            # Walk through all directories in downloads root
            for current_dir, dirs, files in os.walk(self.downloads_root):
                current_path = Path(current_dir)
                
                # Skip root directory itself
                if current_path == self.downloads_root:
                    continue
                
                stats["scanned"] += 1
                
                # Check if directory has expired TTL
                if not self._is_directory_expired(current_path):
                    continue  # Still valid, skip
                
                stats["expired"] += 1
                
                # Check if directory is locked
                if self._is_directory_locked(current_path):
                    stats["locked"] += 1
                    logger.debug(f"Directory locked, skipping: {current_path}")
                    continue
                
                # Try to lock directory
                if not self._lock_directory(current_path):
                    stats["locked"] += 1
                    logger.debug(f"Failed to lock directory: {current_path}")
                    continue
                
                try:
                    # Copy to permanent storage if enabled
                    if PERMANENT_SAVE:
                        if self._copy_to_permanent_storage(current_path):
                            stats["copied"] += 1
                        else:
                            stats["errors"] += 1
                    
                    # Remove directory from cache
                    if self._remove_directory(current_path):
                        stats["removed"] += 1
                    else:
                        stats["errors"] += 1
                        
                finally:
                    # Always unlock directory
                    self._unlock_directory(current_path)
                    
        except Exception as e:
            logger.error(f"Error during cleanup scan: {e}")
            stats["errors"] += 1
        
        logger.info(f"Cleanup completed: {stats}")
        return stats
    
    def get_cleanup_stats(self) -> Dict[str, any]:
        """Get current cleanup statistics and status."""
        return {
            "enabled": self.enabled,
            "downloads_root": str(self.downloads_root),
            "permanent_save_enabled": PERMANENT_SAVE,
            "permanent_save_dir": PERMANENT_SAVE_DIR if PERMANENT_SAVE else None,
            "redis_available": is_redis_available(),
            "cleanup_interval": DISK_CACHE_CLEANUP_INTERVAL
        }
