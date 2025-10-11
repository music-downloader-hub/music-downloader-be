from __future__ import annotations

import time
from typing import List, Optional

from ..schemas.download_schemas import (
    DownloadRequest,
    BatchDownloadRequest,
    BatchDownloadResponse,
    DebugResponse,
)
from ..schemas.job_schemas import JobResponse
from ..core.debug_parser import parse_debug_tracks
from ..core.dedupe import dedupe_service
from .job_service import JobService


class DownloadService:
    """Service for handling download requests and batch operations."""
    
    def __init__(self, job_service: JobService):
        self.job_service = job_service

    def _extract_download_options(self, request: DownloadRequest) -> dict:
        """Extract download options for deduplication key generation."""
        return {
            "url": request.url,
            "song": request.song,
            "atmos": request.atmos,
            "aac": request.aac,
            "select": request.select,
            "all_album": request.all_album,
            "debug": request.debug,
            "search_type": request.search_type,
            "search_term": request.search_term,
        }

    def build_cli_args(self, request: DownloadRequest) -> List[str]:
        """Build CLI arguments from download request."""
        args: List[str] = []
        
        if request.search_type:
            if not request.search_term:
                raise ValueError("search_term is required when search_type is provided")
            args.extend(["--search", request.search_type, request.search_term])
        else:
            if not request.url:
                raise ValueError("url is required when not using search mode")
            
            # Add flags
            if request.song:
                args.append("--song")
            if request.select:
                args.append("--select")
            if request.atmos:
                args.append("--atmos")
            if request.aac:
                args.append("--aac")
            if request.all_album:
                args.append("--all-album")
            if request.debug:
                args.append("--debug")
            
            args.append(request.url)
        
        # Add extra args
        if request.extra_args:
            args.extend(request.extra_args)
        
        return args

    def start_download(self, request: DownloadRequest) -> JobResponse:
        """Start a single download job with deduplication."""
        # Generate content key for deduplication
        options = self._extract_download_options(request)
        content_key = dedupe_service._generate_content_key(
            request.url or f"search:{request.search_type}:{request.search_term}", 
            options
        )
        
        # Check for existing job
        existing_job_id = dedupe_service.get_existing_job(content_key)
        if existing_job_id:
            # Return existing job
            return JobResponse(job_id=existing_job_id)
        
        # Build CLI args and start new job
        args = self.build_cli_args(request)
        job_response = self.job_service.start_job(args)
        
        # Try to acquire lock for this content
        if not dedupe_service.acquire_lock(content_key, job_response.job_id):
            # If we can't acquire lock, another job might have started
            # Check again for existing job
            existing_job_id = dedupe_service.get_existing_job(content_key)
            if existing_job_id:
                # Cancel our job and return existing one
                self.job_service.cancel_job(job_response.job_id)
                return JobResponse(job_id=existing_job_id)
        
        return job_response

    def start_batch_download(self, request: BatchDownloadRequest) -> BatchDownloadResponse:
        """Start multiple download jobs."""
        results: List[JobResponse] = []
        
        for item in request.items:
            try:
                job_response = self.start_download(item)
                results.append(job_response)
            except ValueError:
                # Skip invalid items but continue with others
                continue
            except Exception:
                # Skip failed items but continue with others
                continue
        
        return BatchDownloadResponse(jobs=results)

    def start_debug_download(self, request: DownloadRequest) -> DebugResponse:
        """Start a debug download and return parsed debug information."""
        # Force debug mode
        debug_request = DownloadRequest(
            url=request.url,
            song=request.song,
            select=request.select,
            atmos=request.atmos,
            aac=request.aac,
            all_album=request.all_album,
            debug=True,  # Force debug mode
            search_type=request.search_type,
            search_term=request.search_term,
            extra_args=request.extra_args,
        )
        
        args = self.build_cli_args(debug_request)
        job = self.job_service.start_job(args)
        
        # Wait for job to finish
        while True:
            job_obj = self.job_service.get_job(job.job_id)
            if not job_obj:
                break
            if job_obj.status != "running":
                break
            time.sleep(0.2)
        
        # Get logs and parse debug information
        logs_text = self.job_service.get_job_logs(job.job_id)
        debug_tracks = parse_debug_tracks(logs_text)
        
        # Get final job status
        final_job = self.job_service.get_job(job.job_id)
        status = final_job.status if final_job else "failed"
        return_code = final_job.return_code if final_job else -1
        
        return DebugResponse(
            job_id=job.job_id,
            status=status,
            return_code=return_code,
            debug=debug_tracks,
        )
