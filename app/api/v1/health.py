from __future__ import annotations

from fastapi import APIRouter

from ...core.runner import is_wrapper_running


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "wrapper_running": is_wrapper_running()}


