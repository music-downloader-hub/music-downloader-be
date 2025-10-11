from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

from ...schemas.download_schemas import (
    DownloadRequest,
    BatchDownloadRequest,
    BatchDownloadResponse,
    DebugResponse,
)
from ...schemas.job_schemas import JobSummary
from ...services.job_service import JobService
from ...services.download_service import DownloadService
from ...services.archive_service import ArchiveService


router = APIRouter()
job_service = JobService()
download_service = DownloadService(job_service)
archive_service = ArchiveService()


@router.post("")
def download(request: DownloadRequest):
    try:
        job_response = download_service.start_download(request)
        return {"job_id": job_response.job_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch", response_model=BatchDownloadResponse)
def download_batch(request: BatchDownloadRequest) -> BatchDownloadResponse:
    return download_service.start_batch_download(request)


@router.post("/debug", response_model=DebugResponse)
def download_debug(request: DownloadRequest) -> DebugResponse:
    try:
        return download_service.start_debug_download(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{job_id}", response_model=JobSummary)
def get_job(job_id: str) -> JobSummary:
    job_summary = job_service.get_job_summary(job_id)
    if not job_summary:
        raise HTTPException(status_code=404, detail="job not found")
    return job_summary


@router.get("/{job_id}/logs", response_class=PlainTextResponse)
def get_logs(job_id: str, last_n: Optional[int] = Query(default=None, ge=1)) -> str:
    return job_service.get_job_logs(job_id, last_n)


@router.get("/{job_id}/progress")
def get_progress(job_id: str) -> dict:
    progress = job_service.get_job_progress(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail="job not found")
    
    # Check if job is completed and register in cache
    job = job_service.get_job(job_id)
    if job and job.status == "completed":
        try:
            download_service.register_completed_download(job_id)
        except Exception as e:
            # Log error but don't fail the request
            print(f"[CACHE] Failed to register completed download {job_id}: {e}")
    
    return progress


@router.get("/{job_id}/events")
def sse(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    def event_generator():
        queue: List[dict] = []
        def push(evt: dict):
            queue.append(evt)
        job.sse_subscribers.append(push)
        try:
            yield "event: init\n" + "data: {}\n\n"
            
            # If job is already completed, emit final event immediately
            if job.status in ["completed", "failed"]:
                final_event = {
                    "type": "end",
                    "status": job.status,
                    "return_code": job.return_code
                }
                yield "data: " + __import__("json").dumps(final_event) + "\n\n"
                return
            
            while job.status in ["running", "completed", "failed"] or queue:
                while queue:
                    evt = queue.pop(0)
                    yield "data: " + __import__("json").dumps(evt) + "\n\n"
                import time
                time.sleep(0.2)
        finally:
            try:
                job.sse_subscribers.remove(push)
            except Exception:
                pass

    from starlette.responses import StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")




@router.get("/archive/{path:path}")
def archive(path: str, background_tasks: BackgroundTasks):
    file_response = archive_service.create_archive_from_path(path)
    # Add cleanup task
    def _cleanup():
        try:
            import shutil
            shutil.rmtree(str(file_response.path).rsplit('/', 1)[0], ignore_errors=True)
        except Exception:
            pass
    background_tasks.add_task(_cleanup)
    return file_response


@router.get("/{job_id}/archive")
def archive_by_job(job_id: str, background_tasks: BackgroundTasks):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status == "running":
        raise HTTPException(status_code=409, detail="job still running")
    
    file_response = archive_service.create_archive_from_job(job.created_at)
    # Add cleanup task
    def _cleanup():
        try:
            import shutil
            shutil.rmtree(str(file_response.path).rsplit('/', 1)[0], ignore_errors=True)
        except Exception:
            pass
    background_tasks.add_task(_cleanup)
    return file_response
