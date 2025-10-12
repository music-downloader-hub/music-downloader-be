from __future__ import annotations

import os
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse, FileResponse
from fastapi import BackgroundTasks
from pathlib import Path
import os
import shutil
import tempfile
import re
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

from .core.runner import find_repo_root
from .api.routes import api_router
from .setting.setting import ENABLE_SPOTIFY, ENABLE_DISK_CACHE_MANAGEMENT
from .core.background_scheduler import initialize_scheduler, start_background_scheduler, stop_background_scheduler


app = FastAPI(title="Apple Music Download Service (Python)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.on_event("startup")
async def on_startup() -> None:
    repo_root = find_repo_root()
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    
    # Initialize background scheduler for cache cleanup
    if ENABLE_DISK_CACHE_MANAGEMENT:
        # AM-DL downloads is at project root level
        project_root = repo_root.parent.parent
        downloads_root = project_root / "AM-DL downloads"
        
        # Initialize and start background scheduler
        initialize_scheduler(downloads_root)
        await start_background_scheduler()
        print("[CLEANER] Background scheduler started for cache cleanup")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    # Stop background scheduler
    if ENABLE_DISK_CACHE_MANAGEMENT:
        await stop_background_scheduler()
        print("[CLEANER] Background scheduler stopped")


