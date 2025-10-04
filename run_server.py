from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    os.chdir(str(repo_root))

    from backend_python.app.main import app  # type: ignore

    print("[BOOT] Python API on http://localhost:8080", flush=True)
    uvicorn.run(app, host="localhost", port=8080, reload=False)


if __name__ == "__main__":
    main()

