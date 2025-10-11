from __future__ import annotations

import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

from ..services.cache_service import CacheService

logger = logging.getLogger(__name__)


class CacheScheduler:
    """
    Background scheduler for cache management tasks.
    Handles periodic cleanup of expired directories and quota enforcement.
    """
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the background scheduler."""
        if self._running:
            logger.warning("Cache scheduler is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Cache scheduler started")
    
    async def stop(self):
        """Stop the background scheduler."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cache scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop."""
        from ..setting.setting import DISK_CACHE_CLEANUP_INTERVAL
        
        while self._running:
            try:
                # Run cleanup tasks
                await self._run_cleanup_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(DISK_CACHE_CLEANUP_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache scheduler error: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def _run_cleanup_cycle(self):
        """Run a single cleanup cycle."""
        try:
            # Clean up expired directories
            expired_count = self.cache_service.cleanup_expired_directories()
            
            # Enforce quota if needed
            evicted_count = self.cache_service.enforce_quota()
            
            if expired_count > 0 or evicted_count > 0:
                logger.info(f"Cache cleanup: {expired_count} expired, {evicted_count} evicted")
            
        except Exception as e:
            logger.error(f"Cache cleanup cycle failed: {e}")
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running


# Global scheduler instance
_scheduler: Optional[CacheScheduler] = None


def get_scheduler() -> Optional[CacheScheduler]:
    """Get the global cache scheduler instance."""
    return _scheduler


def initialize_scheduler(cache_service: CacheService) -> CacheScheduler:
    """Initialize the global cache scheduler."""
    global _scheduler
    _scheduler = CacheScheduler(cache_service)
    return _scheduler


async def start_cache_scheduler():
    """Start the global cache scheduler."""
    if _scheduler:
        await _scheduler.start()


async def stop_cache_scheduler():
    """Stop the global cache scheduler."""
    if _scheduler:
        await _scheduler.stop()
