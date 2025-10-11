from __future__ import annotations

import asyncio
import logging
from typing import Optional
from pathlib import Path

from ..services.cleaner_service import CleanerService
from ..setting.setting import DISK_CACHE_CLEANUP_INTERVAL

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """
    Background scheduler for running cleanup tasks periodically.
    Manages the lifecycle of background services.
    """
    
    def __init__(self, downloads_root: Path):
        self.downloads_root = downloads_root
        self.cleaner_service = CleanerService(downloads_root)
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the background scheduler."""
        if self._running:
            logger.warning("Background scheduler is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Background scheduler started")
    
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
        logger.info("Background scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self._running:
            try:
                # Run cleanup cycle
                await self._run_cleanup_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(DISK_CACHE_CLEANUP_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background scheduler error: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def _run_cleanup_cycle(self):
        """Run a single cleanup cycle."""
        try:
            # Run cleanup in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(None, self.cleaner_service.scan_and_cleanup)
            
            # Log summary if there was activity
            if any(stats[key] > 0 for key in ["expired", "removed", "copied", "errors"]):
                logger.info(f"Cleanup cycle completed: {stats}")
            
        except Exception as e:
            logger.error(f"Cleanup cycle failed: {e}")
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
    
    def get_cleanup_stats(self) -> dict:
        """Get cleanup service statistics."""
        return self.cleaner_service.get_cleanup_stats()
    
    async def run_cleanup_now(self) -> dict:
        """Manually trigger cleanup cycle."""
        try:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(None, self.cleaner_service.scan_and_cleanup)
            return stats
        except Exception as e:
            logger.error(f"Manual cleanup failed: {e}")
            return {"error": str(e)}


# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> Optional[BackgroundScheduler]:
    """Get the global background scheduler instance."""
    return _scheduler


def initialize_scheduler(downloads_root: Path) -> BackgroundScheduler:
    """Initialize the global background scheduler."""
    global _scheduler
    _scheduler = BackgroundScheduler(downloads_root)
    return _scheduler


async def start_background_scheduler():
    """Start the global background scheduler."""
    if _scheduler:
        await _scheduler.start()


async def stop_background_scheduler():
    """Stop the global background scheduler."""
    if _scheduler:
        await _scheduler.stop()
