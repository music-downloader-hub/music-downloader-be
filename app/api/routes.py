from __future__ import annotations

from fastapi import APIRouter

from .v1 import downloads, cli, health, spotify, cache
from ..setting.setting import ENABLE_SPOTIFY, ENABLE_DISK_CACHE_MANAGEMENT


api_router = APIRouter()

# Core
api_router.include_router(health.router, tags=["health"])
api_router.include_router(cli.router, prefix="/cli", tags=["cli"])
api_router.include_router(downloads.router, prefix="/downloads", tags=["downloads"])

# Cache management
if ENABLE_DISK_CACHE_MANAGEMENT:
    api_router.include_router(cache.router, prefix="/cache", tags=["cache"])

# Optional (placeholder only, no routes)
if ENABLE_SPOTIFY:
    api_router.include_router(spotify.router, prefix="/auth/spotify", tags=["spotify"])


