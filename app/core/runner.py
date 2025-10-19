from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from subprocess import Popen, PIPE, run
from typing import Callable, Iterable, List, Optional


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Find the Go module root containing main.go in the new structure.
    
    Looks for backend/downloaders/main.go first, then falls back to old logic.
    """
    # Try the new structure first: backend/downloaders/
    current = start or Path(__file__).resolve()
    if current.is_file():
        current = current.parent
    
    # Look for backend/downloaders/main.go
    for parent in [current, *current.parents]:
        downloaders_path = parent / "downloaders"
        if (downloaders_path / "main.go").exists() and (downloaders_path / "go.mod").exists():
            return downloaders_path
    
    # Fallback to old logic (ascend directories)
    for parent in [current, *current.parents]:
        if (parent / "main.go").exists() and (parent / "go.mod").exists():
            return parent
    
    # Final fallback
    return Path(__file__).resolve().parents[2]


def build_command(args: Iterable[str]) -> List[str]:
    """Build the full command to invoke the Go CLI using 'go run main.go'."""
    return ["go", "run", "main.go", *list(args)]




class ProcessIOCollector:
    """Collect stdout/stderr from a subprocess in background threads."""

    def __init__(self, process: Popen, on_line: Optional[Callable[[str], None]] = None):
        self.process = process
        self._lock = threading.Lock()
        self._buffer: List[str] = []
        self._on_line = on_line

        self._stdout_thread = threading.Thread(target=self._pump, args=(process.stdout,), daemon=True)
        self._stderr_thread = threading.Thread(target=self._pump, args=(process.stderr,), daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _pump(self, stream):
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            with self._lock:
                self._buffer.append(line)
            # Mirror to console if requested
            if self._on_line is not None:
                try:
                    self._on_line(line)
                except Exception:
                    # Do not crash on logging errors
                    pass
        try:
            stream.close()
        except Exception:
            pass

    def get_logs(self, last_n: Optional[int] = None) -> str:
        with self._lock:
            if last_n is None or last_n <= 0:
                return "".join(self._buffer)
            return "".join(self._buffer[-last_n:])


def start_process(
    args: Iterable[str],
    env: Optional[dict] = None,
    on_line: Optional[Callable[[str], None]] = None,
) -> tuple[Popen, ProcessIOCollector, Path]:
    """Start the Go CLI process and return the process, IO collector, and working dir."""
    repo_root = find_repo_root()
    command = build_command(args)

    proc = Popen(
        command,
        cwd=str(repo_root),
        env={**os.environ, **(env or {})},
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    collector = ProcessIOCollector(proc, on_line=on_line)
    return proc, collector, repo_root
