from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    args: List[str] = Field(default_factory=list, description="Arguments to pass to the Go CLI (excluding 'go run main.go')")


class JobResponse(BaseModel):
    job_id: str


class JobSummary(BaseModel):
    job_id: str
    status: Literal["running", "completed", "failed", "cancelled"]
    return_code: Optional[int] = None
    args: List[str]
    created_at: float
    updated_at: float


class JobListResponse(BaseModel):
    jobs: List[JobSummary]


class LogsResponse(BaseModel):
    job_id: str
    last_n: Optional[int] = None
    logs: str
