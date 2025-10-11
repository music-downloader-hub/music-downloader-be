from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


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
