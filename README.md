# Apple Music Download Service (FastAPI)

This backend exposes your existing Go downloader over HTTP for downloading from Apple Music.

## Quickstart

1. Virtual environment (Windows PowerShell)
```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r backend/requirements.txt
```

2. Start API
```bash
python backend/run_server.py
```

## Endpoints
- GET /health – health check
- POST /cli/run – run with raw args (excluding `go run main.go`)
  - body: {"args": ["--debug", "<url>"]}
- POST /downloads – create a new download job
  - examples:
```json
{ "url": "https://music.apple.com/...", "atmos": true }
```
```json
{ "search_type": "song", "search_term": "Taylor Swift" }
```
- GET /downloads – list download jobs
- GET /downloads/{download_id} – get job status
- GET /downloads/{download_id}/logs?last_n=500 – get logs
- DELETE /downloads/{download_id} – cancel job

Legacy aliases under `/jobs/*` remain available but are hidden from docs.

## Notes
- The Go CLI still requires `config.yaml`, `wrapper`, `MP4Box`, `mp4decrypt` as before.
- Logs are stored in-memory; use `last_n` to trim responses.
