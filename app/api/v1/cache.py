from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pathlib import Path
from typing import List, Optional

from ...services.cache_service import CacheService
from ...core.runner import find_repo_root

router = APIRouter()


def _get_cache_service() -> CacheService:
    """Get cache service instance."""
    # AM-DL downloads is now at the project root level
    # Go from backend/app/api/v1/ to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    downloads_root = project_root / "AM-DL downloads"
    
    if not downloads_root.exists():
        # Fallback to current directory if not found
        downloads_root = Path.cwd() / "AM-DL downloads"
    
    return CacheService(downloads_root)


@router.get("/stats")
def get_cache_stats():
    """Get cache statistics."""
    cache_service = _get_cache_service()
    return cache_service.get_cache_stats()


@router.get("/directories")
def list_cached_directories(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of directories to return")
):
    """List cached directories with their information."""
    cache_service = _get_cache_service()
    directories = cache_service.list_cached_directories(limit)
    return {
        "directories": directories,
        "count": len(directories)
    }


@router.get("/directories/{path:path}")
def get_directory_info(path: str):
    """Get information about a specific cached directory."""
    cache_service = _get_cache_service()
    info = cache_service.get_directory_info(path)
    
    if not info:
        raise HTTPException(status_code=404, detail="Directory not found in cache")
    
    return info


@router.post("/cleanup")
def cleanup_cache(background_tasks: BackgroundTasks):
    """Trigger cache cleanup (expired directories and quota enforcement)."""
    cache_service = _get_cache_service()
    
    # Run cleanup in background
    background_tasks.add_task(_run_cleanup, cache_service)
    
    return {"message": "Cache cleanup started in background"}


def _run_cleanup(cache_service: CacheService):
    """Background task to run cache cleanup."""
    try:
        # Clean up expired directories
        expired_count = cache_service.cleanup_expired_directories()
        
        # Enforce quota
        evicted_count = cache_service.enforce_quota()
        
        print(f"Cache cleanup completed: {expired_count} expired, {evicted_count} evicted")
    except Exception as e:
        print(f"Cache cleanup failed: {e}")


@router.post("/directories/{path:path}/touch")
def touch_directory(path: str):
    """Update last access time for a directory (extends TTL)."""
    cache_service = _get_cache_service()
    
    # Convert path to full path
    downloads_root = cache_service.downloads_root
    full_path = downloads_root / path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found on disk")
    
    success = cache_service.touch_directory(full_path)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to touch directory")
    
    return {"message": f"Directory {path} touched successfully"}


@router.delete("/directories/{path:path}")
def remove_directory_from_cache(
    path: str,
    remove_files: bool = Query(False, description="Also remove files from disk")
):
    """Remove a directory from cache tracking."""
    cache_service = _get_cache_service()
    
    success = cache_service._remove_directory_from_cache(path, remove_files=remove_files)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove directory from cache")
    
    action = "removed from cache and disk" if remove_files else "removed from cache"
    return {"message": f"Directory {path} {action} successfully"}


@router.post("/directories/{path:path}/register")
def register_directory(path: str):
    """Manually register a directory in the cache system."""
    cache_service = _get_cache_service()
    
    # Convert path to full path
    downloads_root = cache_service.downloads_root
    full_path = downloads_root / path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found on disk")
    
    if not full_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    success = cache_service.register_directory(full_path)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register directory")
    
    return {"message": f"Directory {path} registered successfully"}


@router.post("/clear")
def clear_all_cache():
    """Clear all cache data. Use this when moving download directories."""
    cache_service = _get_cache_service()
    
    if not cache_service.enabled or not cache_service.redis:
        return {"message": "Cache system is disabled or Redis unavailable"}
    
    try:
        # Clear all cache-related keys
        pattern = "dir:*"
        dir_keys = list(cache_service.redis.scan_iter(match=pattern))
        
        pattern = "cache:*"
        cache_keys = list(cache_service.redis.scan_iter(match=pattern))
        
        pattern = "lock:dir:*"
        lock_keys = list(cache_service.redis.scan_iter(match=pattern))
        
        all_keys = dir_keys + cache_keys + lock_keys
        
        if all_keys:
            cache_service.redis.delete(*all_keys)
        
        return {
            "message": "All cache data cleared successfully",
            "cleared_keys": len(all_keys)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e}")