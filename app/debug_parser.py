from __future__ import annotations

import re
from typing import List

from .models import Variant, AvailableFormats, TrackDebug


VARIANT_ROW = re.compile(r"^\|\s*(?P<codec>[^|]+?)\s*\|\s*(?P<audio>[^|]+?)\s*\|\s*(?P<bandwidth>\d+)\s*\|")


def parse_debug_tracks(log_text: str) -> List[TrackDebug]:
    lines = log_text.splitlines()
    tracks: List[TrackDebug] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if _looks_like_track_name(line):
            name = line
            j = i + 1
            while j < len(lines) and "Debug: All Available Variants" not in lines[j]:
                j += 1
            variants: List[Variant] = []
            if j < len(lines):
                j += 1
                while j < len(lines):
                    row = lines[j]
                    if row.strip().startswith("Available Audio Formats"):
                        break
                    m = VARIANT_ROW.search(row)
                    if m:
                        codec = m.group("codec").strip()
                        audio = m.group("audio").strip()
                        bandwidth = int(m.group("bandwidth"))
                        variants.append(Variant(codec=codec, audio_profile=audio, bandwidth=bandwidth))
                    j += 1
                aac = _extract_after_prefix(lines[j:], "AAC             :")
                lossless = _extract_after_prefix(lines[j:], "Lossless        :")
                hires = _extract_after_prefix(lines[j:], "Hi-Res Lossless :")
                atmos = _extract_after_prefix(lines[j:], "Dolby Atmos     :")
                daudio = _extract_after_prefix(lines[j:], "Dolby Audio     :")
                available = AvailableFormats(
                    aac=_normalize_value(aac),
                    lossless=_normalize_value(lossless),
                    hires_lossless=_normalize_value(hires),
                    dolby_atmos=_normalize_value(atmos),
                    dolby_audio=_normalize_value(daudio),
                )
                tracks.append(TrackDebug(name=name, variants=variants, available_formats=available))
                i = j
        i += 1

    return tracks


def _extract_after_prefix(lines: List[str], prefix: str) -> str | None:
    for line in lines:
        if line.strip().startswith(prefix):
            return line.split(":", 1)[-1].strip()
    return None


def _normalize_value(value: str | None) -> str | None:
    if value is None:
        return None
    v = value
    if v.lower().startswith("not available"):
        return "Not Available"
    return v


def _looks_like_track_name(line: str) -> bool:
    return bool(re.match(r"^\d{1,3}\.\s+", line))


