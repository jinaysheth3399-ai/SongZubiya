from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import LogEntry, Song


def list_logs(db: Session, limit: int = 500) -> list[dict]:
    rows = (
        db.query(LogEntry, Song)
        .outerjoin(Song, LogEntry.song_id == Song.id)
        .order_by(LogEntry.created_at.desc(), LogEntry.id.desc())
        .limit(limit)
        .all()
    )
    out = []
    for log, song in rows:
        out.append({
            "id": log.id,
            "time": log.created_at.isoformat() if log.created_at else None,
            "level": log.level,
            "message": log.message,
            "song_id": log.song_id,
            "song_label": (
                f"{song.track_no} - {song.song_name}" if song else None
            ),
        })
    return out
