from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from typing import Dict, Any

from ...core.background_scheduler import get_scheduler
from ...core.runner import find_repo_root

router = APIRouter()


def _get_downloads_root() -> Path:
    """Get the AM-DL downloads root directory."""
    # AM-DL downloads is now at the project root level
    # Go from backend/app/api/v1/ to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    downloads_root = project_root / "AM-DL downloads"
    
    if not downloads_root.exists():
        # Fallback to current directory if not found
        downloads_root = Path.cwd() / "AM-DL downloads"
    
    return downloads_root


@router.get("/stats")
def get_cleaner_stats() -> Dict[str, Any]:
    """Get cleaner service statistics and configuration."""
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Cleaner service not initialized")
    
    return scheduler.get_cleanup_stats()


@router.post("/run")
async def run_cleanup_now(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Manually trigger cleanup cycle."""
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Cleaner service not initialized")
    
    try:
        stats = await scheduler.run_cleanup_now()
        return {
            "message": "Cleanup completed",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/status")
def get_scheduler_status() -> Dict[str, Any]:
    """Get background scheduler status."""
    scheduler = get_scheduler()
    if not scheduler:
        return {
            "running": False,
            "message": "Scheduler not initialized"
        }
    
    return {
        "running": scheduler.is_running(),
        "message": "Scheduler is running" if scheduler.is_running() else "Scheduler is stopped"
    }


@router.post("/start")
async def start_scheduler() -> Dict[str, str]:
    """Start the background scheduler."""
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Cleaner service not initialized")
    
    if scheduler.is_running():
        return {"message": "Scheduler is already running"}
    
    try:
        await scheduler.start()
        return {"message": "Scheduler started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@router.post("/stop")
async def stop_scheduler() -> Dict[str, str]:
    """Stop the background scheduler."""
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Cleaner service not initialized")
    
    if not scheduler.is_running():
        return {"message": "Scheduler is already stopped"}
    
    try:
        await scheduler.stop()
        return {"message": "Scheduler stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")
