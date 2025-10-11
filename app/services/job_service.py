from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Callable

import psutil

from ..core.runner import start_process
from ..core.redis import job_store, is_redis_available
from ..setting.setting import ENABLE_REDIS_LOGS, ENABLE_REDIS_PROGRESS, ENABLE_PERFORMANCE_LOGGING
from ..core.dedupe import dedupe_service
from ..schemas.job_schemas import JobResponse, JobSummary


JobStatus = Literal["running", "completed", "failed", "cancelled"]


@dataclass
class Progress:
    phase: Optional[str] = None  # Downloading/Decrypting
    percent: Optional[int] = None
    speed: Optional[str] = None
    downloaded: Optional[str] = None
    total: Optional[str] = None
    updated_at: float = field(default_factory=lambda: time.time())


@dataclass
class Job:
    job_id: str
    args: List[str]
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    status: JobStatus = "running"
    return_code: Optional[int] = None
    process: Optional[psutil.Process] = None
    io_collector: Optional[object] = None
    progress: Progress = field(default_factory=Progress)
    sse_subscribers: List[Callable[[dict], None]] = field(default_factory=list, repr=False)


class JobService:
    """Service for managing download jobs with Redis persistence."""
    
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._use_redis = is_redis_available()

    def _parse_progress_line(self, job: Job, line: str) -> None:
        """Parse progress information from CLI output."""
        text = line.strip()
        # Examples: "Downloading...  73%  (17/24 MB, 20 MB/s)"
        if "Downloading..." in text or "Decrypting..." in text:
            try:
                phase = "Downloading" if "Downloading..." in text else "Decrypting"
                percent = None
                downloaded = None
                total = None
                speed = None
                # Extract percent
                for token in text.split():
                    if token.endswith("%") and token[:-1].isdigit():
                        percent = int(token[:-1])
                        break
                # Extract sizes and speed within parentheses
                if "(" in text and ")" in text:
                    inner = text[text.find("(") + 1:text.find(")")]
                    parts = [p.strip() for p in inner.split(",")]
                    if parts:
                        size_part = parts[0]  # like "17/24 MB" or "1.6/24 MB"
                        size_tokens = size_part.split()
                        if size_tokens:
                            downloaded = size_tokens[0]
                            total = size_tokens[-1]
                    if len(parts) > 1:
                        speed = parts[1]
                job.progress = Progress(
                    phase=phase,
                    percent=percent,
                    speed=speed,
                    downloaded=downloaded,
                    total=total,
                )
                # Save progress to Redis (only if enabled for maximum performance)
                if self._use_redis and ENABLE_REDIS_PROGRESS:
                    progress_data = {
                        "phase": phase or "",
                        "percent": str(percent) if percent is not None else "",
                        "speed": speed or "",
                        "downloaded": downloaded or "",
                        "total": total or "",
                        "updated_at": str(job.progress.updated_at)
                    }
                    job_store.save_progress(job.job_id, progress_data)
                
                self._emit(job, {"type": "progress", **job.progress.__dict__})
            except Exception:
                pass

    def _emit(self, job: Job, event: dict) -> None:
        """Emit SSE event to subscribers."""
        for cb in list(job.sse_subscribers):
            try:
                cb(event)
            except Exception:
                pass

    def start_job(self, args: List[str]) -> JobResponse:
        """Start a new download job."""
        job_id = uuid.uuid4().hex
        start_time = time.time()

        def mirror(line: str) -> None:
            # Only parse progress if Redis progress is enabled (performance optimization)
            if ENABLE_REDIS_PROGRESS or ENABLE_REDIS_LOGS:
                self._parse_progress_line(job, line)
            # Save log line to Redis (only if enabled for performance)
            if self._use_redis and ENABLE_REDIS_LOGS:
                job_store.append_log(job.job_id, line.strip())
            
            # Performance logging
            if ENABLE_PERFORMANCE_LOGGING and "Downloading..." in line:
                elapsed = time.time() - start_time
                print(f"[PERF] Job {job_id[:8]} - {elapsed:.1f}s - {line.strip()}")

        proc, collector, _ = start_process(args, on_line=mirror)
        ps_proc = psutil.Process(proc.pid)
        job = Job(job_id=job_id, args=list(args), process=ps_proc, io_collector=collector)

        def waiter():
            return_code = proc.wait()
            with self._lock:
                job.return_code = return_code
                job.updated_at = time.time()
                if job.status != "cancelled":
                    job.status = "completed" if return_code == 0 else "failed"
                
                # Update job in Redis
                if self._use_redis:
                    job_data = {
                        "job_id": job.job_id,
                        "args": json.dumps(job.args),
                        "created_at": str(job.created_at),
                        "updated_at": str(job.updated_at),
                        "status": job.status,
                        "return_code": str(job.return_code) if job.return_code is not None else ""
                    }
                    job_store.save_job(job_id, job_data)
                
                # Release deduplication lock when job completes
                # Extract content key from job args (first arg is usually URL)
                if job.args:
                    try:
                        # Try to find content key by checking all possible locks
                        # This is a simple approach - in production you might want to store content_key with job
                        dedupe_service.cleanup_expired_locks()
                    except Exception as e:
                        print(f"[DEDUPE] Failed to cleanup locks: {e}")
                    
            self._emit(job, {"type": "end", "status": job.status, "return_code": return_code})

        with self._lock:
            self._jobs[job_id] = job
            
            # Save job to Redis
            if self._use_redis:
                job_data = {
                    "job_id": job.job_id,
                    "args": json.dumps(job.args),
                    "created_at": str(job.created_at),
                    "updated_at": str(job.updated_at),
                    "status": job.status,
                    "return_code": str(job.return_code) if job.return_code is not None else ""
                }
                job_store.save_job(job_id, job_data)

        threading.Thread(target=waiter, daemon=True).start()
        self._emit(job, {"type": "start", "job_id": job_id})
        return JobResponse(job_id=job.job_id)

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID from memory or Redis."""
        with self._lock:
            # Try in-memory first
            job = self._jobs.get(job_id)
            if job:
                return job
            
            # Try Redis if available
            if self._use_redis:
                job_data = job_store.get_job(job_id)
                if job_data:
                    # Reconstruct Job object from Redis data
                    job = Job(
                        job_id=job_data["job_id"],
                        args=job_data["args"],
                        created_at=job_data["created_at"],
                        updated_at=job_data["updated_at"],
                        status=job_data["status"],
                        return_code=job_data.get("return_code")
                    )
                    # Load progress from Redis
                    progress_data = job_store.get_progress(job_id)
                    if progress_data:
                        job.progress = Progress(
                            phase=progress_data.get("phase"),
                            percent=int(progress_data["percent"]) if progress_data.get("percent") else None,
                            speed=progress_data.get("speed"),
                            downloaded=progress_data.get("downloaded"),
                            total=progress_data.get("total"),
                            updated_at=float(progress_data.get("updated_at", 0))
                        )
                    return job
            return None

    def get_job_summary(self, job_id: str) -> Optional[JobSummary]:
        """Get job summary for API response."""
        job = self.get_job(job_id)
        if not job:
            return None
        return JobSummary(
            job_id=job.job_id,
            status=job.status,
            return_code=job.return_code,
            args=job.args,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def get_job_logs(self, job_id: str, last_n: Optional[int] = None) -> str:
        """Get job logs from Redis or in-memory."""
        # Try Redis first if available
        if self._use_redis:
            logs = job_store.get_logs(job_id, last_n)
            if logs:
                return "\n".join(logs)
        
        # Fallback to in-memory
        job = self.get_job(job_id)
        if not job or not job.io_collector:
            return ""
        return job.io_collector.get_logs(last_n=last_n)

    def get_job_progress(self, job_id: str) -> Optional[dict]:
        """Get job progress for API response."""
        job = self.get_job(job_id)
        if not job:
            return None
        p = job.progress
        return {
            "phase": p.phase,
            "percent": p.percent,
            "speed": p.speed,
            "downloaded": p.downloaded,
            "total": p.total,
            "updated_at": p.updated_at,
        }

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        job = self.get_job(job_id)
        if not job or not job.process:
            return False
        try:
            for child in job.process.children(recursive=True):
                try:
                    child.terminate()
                except Exception:
                    pass
            job.process.terminate()
            job.status = "cancelled"
            self._emit(job, {"type": "cancelled"})
            return True
        except Exception:
            return False

    def list_jobs(self) -> List[Job]:
        """List all jobs (in-memory only for now)."""
        with self._lock:
            return list(self._jobs.values())
