from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Callable

import psutil

from .runner import start_process


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


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def _parse_progress_line(self, job: Job, line: str) -> None:
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
                self._emit(job, {"type": "progress", **job.progress.__dict__})
            except Exception:
                pass

    def _emit(self, job: Job, event: dict) -> None:
        for cb in list(job.sse_subscribers):
            try:
                cb(event)
            except Exception:
                pass

    def start(self, args: List[str]) -> Job:
        job_id = uuid.uuid4().hex

        def mirror(line: str) -> None:
            self._parse_progress_line(job, line)

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
            self._emit(job, {"type": "end", "status": job.status, "return_code": return_code})

        with self._lock:
            self._jobs[job_id] = job

        threading.Thread(target=waiter, daemon=True).start()
        self._emit(job, {"type": "start", "job_id": job_id})
        return job

    def list(self) -> List[Job]:
        with self._lock:
            return list(self._jobs.values())

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def logs(self, job_id: str, last_n: Optional[int] = None) -> str:
        job = self.get(job_id)
        if not job or not job.io_collector:
            return ""
        return job.io_collector.get_logs(last_n=last_n)

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
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




