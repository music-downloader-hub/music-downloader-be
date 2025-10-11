from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...schemas.job_schemas import RunRequest
from ...services.job_service import JobService


router = APIRouter()
job_service = JobService()


@router.post("/run")
def run_job(request: RunRequest):
    if not request.args:
        raise HTTPException(status_code=400, detail="args must not be empty")
    job_response = job_service.start_job(request.args)
    return {"job_id": job_response.job_id}


