from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import Playlist, Song, SongStatus


_FAILED_STATUSES = {
    SongStatus.FAILED_NO_RESULT,
    SongStatus.FAILED_AUDIO,
    SongStatus.FAILED_VERIFICATION,
    SongStatus.FAILED_UPLOAD,
    SongStatus.SKIPPED_LOW_CONFIDENCE,
}


def list_playlists_with_progress(db: Session) -> list[dict]:
    playlists = db.query(Playlist).order_by(Playlist.name).all()
    out = []
    for pl in playlists:
        total = len(pl.songs)
        completed = sum(1 for s in pl.songs if s.status == SongStatus.COMPLETED)
        failed = sum(1 for s in pl.songs if s.status in _FAILED_STATUSES)
        review = sum(1 for s in pl.songs if s.status == SongStatus.NEEDS_REVIEW)
        progress = (completed / total) if total else 0.0
        out.append({
            "id": pl.id,
            "name": pl.name,
            "drive_root_name": pl.drive_root_name,
            "drive_folder_id": pl.drive_folder_id,
            "total": total,
            "completed": completed,
            "failed": failed,
            "needs_review": review,
            "progress_pct": round(progress * 100, 1),
        })
    return out


def overall_status(db: Session) -> dict:
    total = db.query(func.count(Song.id)).scalar() or 0
    by_status = dict(
        db.query(Song.status, func.count(Song.id)).group_by(Song.status).all()
    )
    completed = by_status.get(SongStatus.COMPLETED, 0)
    failed = sum(by_status.get(s, 0) for s in _FAILED_STATUSES)
    needs_review = by_status.get(SongStatus.NEEDS_REVIEW, 0)
    pending = sum(
        by_status.get(s, 0)
        for s in (
            SongStatus.PENDING,
            SongStatus.SEARCHING,
            SongStatus.APPROVED,
            SongStatus.PROCESSING_AUDIO,
            SongStatus.VERIFYING_FILE,
            SongStatus.UPLOADING,
        )
    )
    return {
        "total_songs": total,
        "completed": completed,
        "failed": failed,
        "needs_review": needs_review,
        "pending": pending,
        "progress_pct": round((completed / total) * 100, 1) if total else 0.0,
        "by_status": by_status,
    }
