from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from subprocess import Popen, PIPE, run
from typing import Callable, Iterable, List, Optional


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Ascend directories until we find the project root containing main.go.

    Falls back to two levels above this file if not found.
    """
    current = start or Path(__file__).resolve()
    if current.is_file():
        current = current.parent
    for parent in [current, *current.parents]:
        if (parent / "main.go").exists() and (parent / "go.mod").exists():
            return parent
    return Path(__file__).resolve().parents[2]


def build_command(args: Iterable[str]) -> List[str]:
    """Build the full command to invoke the Go CLI using 'go run main.go'."""
    return ["go", "run", "main.go", *list(args)]


def docker_available() -> bool:
    try:
        run(["docker", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        print("[WRAPPER][ERROR] Docker is not available. Please install/start Docker Desktop.", flush=True)
        return False


def ensure_wrapper_built(repo_root: Path) -> bool:
    if not docker_available():
        return False
    try:
        existing = run(["docker", "images", "-q", "wrapper"], capture_output=True, text=True)
        if existing.stdout.strip():
            return True
        print("[WRAPPER] Building Docker image 'wrapper'...", flush=True)
        result = run(["docker", "build", "--tag", "wrapper", "."], cwd=str(repo_root / "wrapper"), capture_output=True, text=True)
        if result.returncode != 0:
            print("[WRAPPER][ERROR] Docker build failed.", flush=True)
            if result.stderr:
                print(f"[WRAPPER][ERROR] {result.stderr.strip()}", flush=True)
            print("[WRAPPER][HINT] Ensure Docker Desktop is running and you have internet access.", flush=True)
            return False
        print("[WRAPPER] Build complete.", flush=True)
        return True
    except Exception as e:
        print(f"[WRAPPER][ERROR] Build failed: {e}", flush=True)
        return False


_WRAPPER_PROC: Optional[Popen] = None
_WRAPPER_STARTED_BY_APP: bool = False


def start_wrapper(repo_root: Path, login_args: Optional[str] = None) -> Optional[Popen]:
    if not ensure_wrapper_built(repo_root):
        return None
    data_dir = repo_root / "wrapper" / "rootfs" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    args = login_args or "-H 0.0.0.0"
    volume_spec = f"{str(data_dir)}:/app/rootfs/data"
    cmd = [
        "docker", "run", "--rm",
        "-v", volume_spec,
        "-p", "10020:10020",
        "-e", f"args={args}",
        "--name", "wrapper-service",
        "wrapper",
    ]
    print("[WRAPPER] Starting service...", flush=True)
    try:
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, text=True, encoding="utf-8", errors="replace")

        def _pump(stream):
            if stream is None:
                return
            for line in iter(stream.readline, ""):
                print(f"[WRAPPER] {line}", end="", flush=True)
            try:
                stream.close()
            except Exception:
                pass

        threading.Thread(target=_pump, args=(proc.stdout,), daemon=True).start()
        threading.Thread(target=_pump, args=(proc.stderr,), daemon=True).start()

        # Brief readiness check: ensure process did not exit immediately
        time.sleep(1.0)
        if proc.poll() is not None:
            print("[WRAPPER][ERROR] Wrapper process exited during startup.", flush=True)
            print("[WRAPPER][HINT] Make sure Docker Desktop is running and port 10020 is free.", flush=True)
            return None
        global _WRAPPER_PROC
        _WRAPPER_PROC = proc
        global _WRAPPER_STARTED_BY_APP
        _WRAPPER_STARTED_BY_APP = True
        return proc
    except Exception as e:
        print(f"[WRAPPER][ERROR] Failed to start: {e}", flush=True)
        return None


def stop_wrapper() -> None:
    if not docker_available():
        return
    # Stop the container if it is currently running, regardless of who started it
    if not is_wrapper_running():
        return
    try:
        run(["docker", "stop", "wrapper-service"], capture_output=True)
    except Exception:
        pass
    finally:
        # Reset local flag just in case
        global _WRAPPER_STARTED_BY_APP
        _WRAPPER_STARTED_BY_APP = False


def is_wrapper_running() -> bool:
    """Return True if the Docker container 'wrapper-service' is currently running."""
    if not docker_available():
        return False
    try:
        # Match exact name using anchored regex ^/wrapper-service$
        result = run(
            [
                "docker",
                "ps",
                "-q",
                "--filter",
                "name=^/wrapper-service$",
            ],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


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


