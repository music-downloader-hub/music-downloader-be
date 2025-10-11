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

from .core.runner import find_repo_root, start_wrapper, stop_wrapper, is_wrapper_running
from .api.routes import api_router
from .setting.setting import ENABLE_SPOTIFY


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
def on_startup() -> None:
    repo_root = find_repo_root()
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    username = os.environ.get("WRAPPER_USERNAME")
    password = os.environ.get("WRAPPER_PASSWORD")
    login_args = os.environ.get("WRAPPER_ARGS")
    if username and password:
        extra = f" {login_args}" if login_args else ""
        login_args = f"-L {username}:{password}{extra}"
    # If wrapper is already running (e.g., previously launched), skip starting and continue
    if is_wrapper_running():
        print("[WRAPPER] Detected existing 'wrapper-service' container. Skipping start.")
        return
    proc = start_wrapper(repo_root, login_args=login_args)
    if proc is None:
        # If start failed but container is running (race), continue
        if is_wrapper_running():
            print("[WRAPPER] Service appears to be running after start attempt. Continuing.")
            return
        raise RuntimeError("Wrapper service failed to start. Ensure Docker Desktop is running.")


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_wrapper()


