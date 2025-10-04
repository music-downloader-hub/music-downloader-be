from __future__ import annotations

from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    args: List[str] = Field(default_factory=list, description="Arguments to pass to the Go CLI (excluding 'go run main.go')")


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


# Debug schemas
class Variant(BaseModel):
    codec: str
    audio_profile: str
    bandwidth: int


class AvailableFormats(BaseModel):
    aac: Optional[str] = None
    lossless: Optional[str] = None
    hires_lossless: Optional[str] = None
    dolby_atmos: Optional[str] = None
    dolby_audio: Optional[str] = None


class DebugInfo(BaseModel):
    variants: List[Variant] = Field(default_factory=list)
    available_formats: AvailableFormats


class TrackDebug(BaseModel):
    name: str
    variants: List[Variant]
    available_formats: AvailableFormats


class DebugResponse(BaseModel):
    job_id: str
    status: Literal["completed", "failed", "cancelled"]
    return_code: int
    debug: List[TrackDebug]


class DownloadResponse(BaseModel):
    job_id: str
    status: Literal["completed", "failed", "cancelled"]
    return_code: int
    name: Optional[str] = None
    variant: Optional[Variant] = None
    format: Optional[AvailableFormats] = None


