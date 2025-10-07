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
import httpx

from .jobs import JobManager
from .models import (
    DownloadRequest,
    JobListResponse,
    JobResponse,
    JobSummary,
    LogsResponse,
    RunRequest,
    DebugResponse,
    BatchDownloadRequest,
    BatchDownloadResponse,
)
from .debug_parser import parse_debug_tracks
from .runner import find_repo_root, start_wrapper, stop_wrapper, is_wrapper_running


app = FastAPI(title="Apple Music Download Service (Python)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
jobs = JobManager()

# In-memory cache for Spotify Client Credentials token
_spotify_access_token: str | None = None
_spotify_token_expires_at: float = 0.0


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


@app.get("/auth/spotify/token")
def spotify_token() -> dict:
    global _spotify_access_token, _spotify_token_expires_at
    # Return cached token if valid for at least 30 seconds
    now = time.time()
    if _spotify_access_token and (_spotify_token_expires_at - now) > 30:
        return {"access_token": _spotify_access_token}

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Spotify credentials not configured on server")

    try:
        resp = httpx.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to obtain Spotify token: {e}")

    data = resp.json()
    token = data.get("access_token")
    expires_in = int(data.get("expires_in") or 3600)
    if not token:
        raise HTTPException(status_code=502, detail="Spotify token missing in response")

    _spotify_access_token = token
    _spotify_token_expires_at = now + max(0, expires_in - 30)
    return {"access_token": token}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/cli/run")
def run_job(request: RunRequest):
    if not request.args:
        raise HTTPException(status_code=400, detail="args must not be empty")
    job = jobs.start(request.args)
    return {"job_id": job.job_id}


@app.post("/downloads")
def download(request: DownloadRequest):
    args: List[str] = []
    if request.search_type:
        if not request.search_term:
            raise HTTPException(status_code=400, detail="search_term is required when search_type is provided")
        args.extend(["--search", request.search_type, request.search_term])
    else:
        if not request.url:
            raise HTTPException(status_code=400, detail="url is required when not using search mode")
        if request.song:
            args.append("--song")
        if request.select:
            args.append("--select")
        if request.atmos:
            args.append("--atmos")
        if request.aac:
            args.append("--aac")
        if request.all_album:
            args.append("--all-album")
        if request.debug:
            args.append("--debug")
        args.append(request.url)
    if request.extra_args:
        args.extend(request.extra_args)

    job = jobs.start(args)
    return {"job_id": job.job_id}


@app.post("/downloads/batch", response_model=BatchDownloadResponse)
def download_batch(request: BatchDownloadRequest) -> BatchDownloadResponse:
    results: List[JobResponse] = []
    for item in request.items:
        try:
            # Reuse the same logic as single download
            args: List[str] = []
            if item.search_type:
                if not item.search_term:
                    raise HTTPException(status_code=400, detail="search_term is required when search_type is provided")
                args.extend(["--search", item.search_type, item.search_term])
            else:
                if not item.url:
                    raise HTTPException(status_code=400, detail="url is required when not using search mode")
                if item.song:
                    args.append("--song")
                if item.select:
                    args.append("--select")
                if item.atmos:
                    args.append("--atmos")
                if item.aac:
                    args.append("--aac")
                if item.all_album:
                    args.append("--all-album")
                if item.debug:
                    args.append("--debug")
                args.append(item.url)
            if item.extra_args:
                args.extend(item.extra_args)

            job = jobs.start(args)
            results.append(JobResponse(job_id=job.job_id))
        except HTTPException:
            # Bubble HTTP errors (malformed item)
            raise
        except Exception:
            # Skip failed item creation but continue others
            continue

    return BatchDownloadResponse(jobs=results)


@app.post("/downloads/debug", response_model=DebugResponse)
def download_debug(request: DownloadRequest) -> DebugResponse:
    args: List[str] = []
    if request.search_type:
        if not request.search_term:
            raise HTTPException(status_code=400, detail="search_term is required when search_type is provided")
        args.extend(["--search", request.search_type, request.search_term])
    else:
        if not request.url:
            raise HTTPException(status_code=400, detail="url is required when not using search mode")
        if request.song:
            args.append("--song")
        if request.select:
            args.append("--select")
        if request.atmos:
            args.append("--atmos")
        if request.aac:
            args.append("--aac")
        if request.all_album:
            args.append("--all-album")
        # Force debug mode for this endpoint regardless of input
        args.append("--debug")
        args.append(request.url)
    if request.extra_args:
        args.extend(request.extra_args)

    job = jobs.start(args)

    # Wait for job to finish, then parse logs
    while job.status == "running":
        time.sleep(0.2)

    logs_text = jobs.logs(job.job_id)
    debug_tracks = parse_debug_tracks(logs_text)

    return DebugResponse(
        job_id=job.job_id,
        status=job.status,  # completed | failed | cancelled
        return_code=job.return_code or -1,
        debug=debug_tracks,
    )


@app.get("/downloads/{job_id}", response_model=JobSummary)
def get_job(job_id: str) -> JobSummary:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return JobSummary(
        job_id=job.job_id,
        status=job.status,
        return_code=job.return_code,
        args=job.args,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@app.get("/downloads/{job_id}/logs", response_class=PlainTextResponse)
def get_logs(job_id: str, last_n: Optional[int] = Query(default=None, ge=1)) -> str:
    return jobs.logs(job_id, last_n=last_n)


@app.get("/downloads/{job_id}/progress")
def get_progress(job_id: str) -> dict:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    p = job.progress
    return {
        "phase": p.phase,
        "percent": p.percent,
        "speed": p.speed,
        "downloaded": p.downloaded,
        "total": p.total,
        "updated_at": p.updated_at,
    }


@app.get("/downloads/{job_id}/events")
def sse(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    def event_generator():
        queue: List[dict] = []
        def push(evt: dict):
            queue.append(evt)
        job.sse_subscribers.append(push)
        try:
            yield "event: init\n" + "data: {}\n\n"
            while job.status == "running" or queue:
                while queue:
                    evt = queue.pop(0)
                    yield "data: " + __import__("json").dumps(evt) + "\n\n"
                time.sleep(0.2)
        finally:
            try:
                job.sse_subscribers.remove(push)
            except Exception:
                pass

    from starlette.responses import StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.delete("/downloads/{job_id}")
def cancel(job_id: str) -> dict:
    ok = jobs.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found or done")
    return {"cancelled": True, "job_id": job_id}


def _downloads_root() -> Path:
    return find_repo_root() / "AM-DL downloads"


def _validate_subpath(path: str) -> Path:
    root = _downloads_root().resolve()
    target = (root / path).resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=400, detail="invalid path")
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="directory not found")
    return target


def _sanitize_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join(("_" if c in invalid else c) for c in name)
    return cleaned.strip().rstrip(".-")


def _zip_filename_for_target(target: Path) -> str:
    root = _downloads_root().resolve()
    try:
        rel_parts = list(target.resolve().relative_to(root).parts)
    except Exception:
        rel_parts = [target.name]

    song_name: str | None = None
    try:
        for p in target.rglob("*.m4a"):
            stem = p.stem
            stem = re.sub(r"^\d+\.?\s*", "", stem)
            song_name = stem
            break
    except Exception:
        pass

    parts = rel_parts[:]
    if song_name:
        parts.append(song_name)
    base = " - ".join(parts)
    return f"{_sanitize_filename(base)}.zip"


@app.get("/archive")
def archive(path: str, background: BackgroundTasks):
    # Validate path under downloads root
    target = _validate_subpath(path)

    # Create temporary zip
    tmp_dir = tempfile.mkdtemp(prefix="amd-zip-")
    base_name = Path(tmp_dir) / "archive"
    try:
        zip_path = shutil.make_archive(str(base_name), "zip", root_dir=str(target))
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"failed to create zip: {e}")

    filename = _zip_filename_for_target(target)

    def _cleanup():
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    background.add_task(_cleanup)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=filename,
    )


def _find_best_output_dir(job_created_at: float) -> Path | None:
    root = _downloads_root().resolve()
    if not root.exists():
        return None
    best_dir = None
    best_mtime = -1.0
    # Consider dirs modified after job start minus a small buffer
    threshold = job_created_at - 300.0
    for current_root, dirs, files in os.walk(root):
        # Compute latest mtime within this directory
        latest = 0.0
        for name in files:
            try:
                p = Path(current_root) / name
                m = p.stat().st_mtime
                if m > latest:
                    latest = m
            except Exception:
                pass
        # Fallback to directory mtime if no files
        try:
            dir_m = Path(current_root).stat().st_mtime
            latest = max(latest, dir_m)
        except Exception:
            pass
        if latest >= threshold and latest > best_mtime:
            best_mtime = latest
            best_dir = Path(current_root)
    return best_dir


@app.get("/downloads/{job_id}/archive")
def archive_by_job(job_id: str, background: BackgroundTasks):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status == "running":
        raise HTTPException(status_code=409, detail="job still running")
    target = _find_best_output_dir(job.created_at)
    if not target:
        raise HTTPException(status_code=404, detail="output directory not found")
    # Create temporary zip
    tmp_dir = tempfile.mkdtemp(prefix="amd-zip-")
    base_name = Path(tmp_dir) / "archive"
    try:
        zip_path = shutil.make_archive(str(base_name), "zip", root_dir=str(target))
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"failed to create zip: {e}")

    filename = _zip_filename_for_target(target)

    def _cleanup():
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    background.add_task(_cleanup)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=filename,
    )

