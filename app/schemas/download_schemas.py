from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from .debug_schemas import Variant, AvailableFormats, TrackDebug
from .job_schemas import JobResponse


class DownloadRequest(BaseModel):
    url: Optional[str] = Field(default=None, description="Apple Music URL (album/playlist/artist/song)")
    song: bool = False
    atmos: bool = False
    aac: bool = False
    select: bool = False
    all_album: bool = False
    debug: bool = False

    search_type: Optional[Literal["song", "album", "artist"]] = Field(default=None, description="Use interactive search mode")
    search_term: Optional[str] = None

    extra_args: List[str] = Field(default_factory=list, description="Additional raw CLI args to pass through")


class DownloadResponse(BaseModel):
    job_id: str
    status: Literal["completed", "failed", "cancelled"]
    return_code: int
    name: Optional[str] = None
    variant: Optional[Variant] = None
    format: Optional[AvailableFormats] = None


class DebugResponse(BaseModel):
    job_id: str
    status: Literal["completed", "failed", "cancelled"]
    return_code: int
    debug: List[TrackDebug]


class BatchDownloadRequest(BaseModel):
    items: List[DownloadRequest] = Field(default_factory=list)


class BatchDownloadResponse(BaseModel):
    jobs: List[JobResponse]
