from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import FileResponse

from ..core.runner import find_repo_root


class ArchiveService:
    """Service for creating and managing download archives."""
    
    def __init__(self):
        # AM-DL downloads is now at the project root level
        # find_repo_root() returns backend/modules/downloaders/
        # So we need to go up 3 levels: downloaders -> modules -> backend -> project_root
        project_root = find_repo_root().parent.parent.parent
        self.downloads_root = project_root / "AM-DL downloads"

    def _validate_subpath(self, path: str) -> Path:
        """Validate that path is under downloads root."""
        root = self.downloads_root.resolve()
        target = (root / path).resolve()
        if not str(target).startswith(str(root)):
            raise HTTPException(status_code=400, detail="invalid path")
        if not target.exists() or not target.is_dir():
            raise HTTPException(status_code=404, detail="directory not found")
        return target

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for safe download."""
        invalid = '<>:"/\\|?*'
        cleaned = "".join(("_" if c in invalid else c) for c in name)
        return cleaned.strip().rstrip(".-")

    def _zip_filename_for_target(self, target: Path) -> str:
        """Generate appropriate zip filename for target directory."""
        root = self.downloads_root.resolve()
        try:
            rel_parts = list(target.resolve().relative_to(root).parts)
        except Exception:
            rel_parts = [target.name]
        
        # Try to find song name from .m4a files
        song_name: Optional[str] = None
        try:
            for p in target.rglob("*.m4a"):
                stem = p.stem
                stem = re.sub(r"^\d+\.?\s*", "", stem)
                song_name = stem
                break
        except Exception:
            pass
        
        parts = rel_parts[:]
        if song_name:
            parts.append(song_name)
        base = " - ".join(parts)
        return f"{self._sanitize_filename(base)}.zip"

    def _find_best_output_dir(self, job_created_at: float) -> Optional[Path]:
        """Find the most likely output directory for a job."""
        root = self.downloads_root.resolve()
        if not root.exists():
            return None
        
        # Find the most recently modified directory
        best_dir = None
        best_mtime = -1.0
        
        for current_root, dirs, files in os.walk(root):
            # Compute latest mtime within this directory
            latest = 0.0
            for name in files:
                try:
                    p = Path(current_root) / name
                    m = p.stat().st_mtime
                    if m > latest:
                        latest = m
                except Exception:
                    pass
            
            # Fallback to directory mtime if no files
            try:
                dir_m = Path(current_root).stat().st_mtime
                latest = max(latest, dir_m)
            except Exception:
                pass
            
            # Find the most recent directory (ignore job creation time)
            if latest > best_mtime:
                best_mtime = latest
                best_dir = Path(current_root)
        
        return best_dir

    def create_archive_from_path(self, path: str) -> FileResponse:
        """Create archive from directory path."""
        target = self._validate_subpath(path)
        
        # Create temporary zip
        tmp_dir = tempfile.mkdtemp(prefix="amd-zip-")
        base_name = Path(tmp_dir) / "archive"
        
        try:
            zip_path = shutil.make_archive(str(base_name), "zip", root_dir=str(target))
        except Exception as e:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"failed to create zip: {e}")
        
        filename = self._zip_filename_for_target(target)
        
        def _cleanup():
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass
        
        # Note: BackgroundTasks cleanup should be handled by the API layer
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=filename,
        )

    def create_archive_from_job(self, job_created_at: float) -> FileResponse:
        """Create archive from job creation time."""
        target = self._find_best_output_dir(job_created_at)
        if not target:
            raise HTTPException(status_code=404, detail="output directory not found")
        
        # Create temporary zip
        tmp_dir = tempfile.mkdtemp(prefix="amd-zip-")
        base_name = Path(tmp_dir) / "archive"
        
        try:
            zip_path = shutil.make_archive(str(base_name), "zip", root_dir=str(target))
        except Exception as e:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"failed to create zip: {e}")
        
        filename = self._zip_filename_for_target(target)
        
        def _cleanup():
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass
        
        # Note: BackgroundTasks cleanup should be handled by the API layer
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=filename,
        )
