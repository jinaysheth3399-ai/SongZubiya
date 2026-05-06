"""FastAPI entrypoint.

Run from the project root with:
    uvicorn backend.main:app --reload
"""
from __future__ import annotations

import threading

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db, init_db
from backend.services import song_service, playlist_service, log_service
from backend.automation.runner import (
    pause_runner,
    process_single_song,
    resume_runner,
    runner_status,
    start_runner,
)
from backend.drive.auth import get_drive_service, reset_service_cache
from backend.drive.uploader import test_drive_connection


app = FastAPI(title=settings.APP_NAME)

# Permissive CORS for local dashboard development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ApproveCandidatePayload(BaseModel):
    song_id: int
    candidate_id: int
    auto_process: bool = True


class SkipPayload(BaseModel):
    reason: str | None = None


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------
@app.get("/api/songs")
def api_list_songs(db: Session = Depends(get_db)):
    return song_service.list_songs(db)


@app.get("/api/playlists")
def api_list_playlists(db: Session = Depends(get_db)):
    return playlist_service.list_playlists_with_progress(db)


@app.get("/api/status")
def api_status(db: Session = Depends(get_db)):
    return {
        **playlist_service.overall_status(db),
        "runner": runner_status(),
    }


@app.get("/api/logs")
def api_logs(limit: int = 500, db: Session = Depends(get_db)):
    return log_service.list_logs(db, limit=limit)


@app.get("/api/songs/{song_id}/candidates")
def api_get_candidates(song_id: int, db: Session = Depends(get_db)):
    if song_service.get_song(db, song_id) is None:
        raise HTTPException(status_code=404, detail="Song not found")
    return song_service.get_candidates(db, song_id)


# ---------------------------------------------------------------------------
# Runner control
# ---------------------------------------------------------------------------
@app.post("/api/start")
def api_start():
    started = start_runner()
    return {"started": started, "runner": runner_status()}


@app.post("/api/pause")
def api_pause():
    pause_runner()
    return {"runner": runner_status()}


@app.post("/api/resume")
def api_resume():
    resume_runner()
    return {"runner": runner_status()}


# ---------------------------------------------------------------------------
# Per-song actions
# ---------------------------------------------------------------------------
@app.post("/api/retry/{song_id}")
def api_retry(song_id: int, db: Session = Depends(get_db)):
    song = song_service.mark_for_retry(db, song_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    # Kick off a single-song run in the background so the API returns fast.
    threading.Thread(target=process_single_song, args=(song.id,), daemon=True).start()
    return {"song": song_service.serialize_song(song)}


@app.post("/api/approve-candidate")
def api_approve_candidate(payload: ApproveCandidatePayload, db: Session = Depends(get_db)):
    song = song_service.approve_candidate(db, payload.song_id, payload.candidate_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song or candidate not found")
    if payload.auto_process:
        threading.Thread(target=process_single_song, args=(song.id,), daemon=True).start()
    return {"song": song_service.serialize_song(song)}


@app.post("/api/skip/{song_id}")
def api_skip(song_id: int, payload: SkipPayload | None = None, db: Session = Depends(get_db)):
    reason = payload.reason if payload else None
    song = song_service.skip_song(db, song_id, reason=reason)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    return {"song": song_service.serialize_song(song)}


# ---------------------------------------------------------------------------
# Drive endpoints
# ---------------------------------------------------------------------------
@app.post("/api/drive/auth")
def api_drive_auth():
    """Trigger the OAuth flow if no valid token is cached yet.

    On first call: opens a browser on the host running uvicorn for consent,
    then writes token.json. If a valid token already exists, this is a no-op.
    """
    reset_service_cache()
    try:
        get_drive_service()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Drive auth failed: {exc}") from exc
    return {"ok": True}


@app.post("/api/drive/test")
def api_drive_test():
    try:
        info = test_drive_connection()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Drive test failed: {exc}") from exc
    return {"ok": True, "drive": info}
