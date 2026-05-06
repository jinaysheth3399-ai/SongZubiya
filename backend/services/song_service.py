from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import Song, SongStatus, YouTubeCandidate, LogEntry


def serialize_song(song: Song) -> dict:
    return {
        "id": song.id,
        "playlist_id": song.playlist_id,
        "playlist_name": song.playlist.name if song.playlist else None,
        "track_no": song.track_no,
        "song_name": song.song_name,
        "artist": song.artist,
        "search_query": song.search_query,
        "selected_youtube_title": song.selected_youtube_title,
        "selected_youtube_channel": song.selected_youtube_channel,
        "selected_youtube_url": song.selected_youtube_url,
        "confidence_score": song.confidence_score,
        "status": song.status,
        "local_file_path": song.local_file_path,
        "drive_file_id": song.drive_file_id,
        "drive_web_link": song.drive_web_link,
        "retry_count": song.retry_count,
        "notes": song.notes,
        "created_at": song.created_at.isoformat() if song.created_at else None,
        "updated_at": song.updated_at.isoformat() if song.updated_at else None,
    }


def serialize_candidate(c: YouTubeCandidate) -> dict:
    return {
        "id": c.id,
        "song_id": c.song_id,
        "title": c.title,
        "channel": c.channel,
        "url": c.url,
        "duration": c.duration,
        "thumbnail_url": c.thumbnail_url,
        "confidence_score": c.confidence_score,
        "rank": c.rank,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def list_songs(db: Session) -> list[dict]:
    songs = db.query(Song).order_by(Song.playlist_id, Song.track_no, Song.id).all()
    return [serialize_song(s) for s in songs]


def get_song(db: Session, song_id: int) -> Song | None:
    return db.query(Song).filter(Song.id == song_id).one_or_none()


def get_candidates(db: Session, song_id: int) -> list[dict]:
    cands = (
        db.query(YouTubeCandidate)
        .filter(YouTubeCandidate.song_id == song_id)
        .order_by(YouTubeCandidate.rank)
        .all()
    )
    return [serialize_candidate(c) for c in cands]


def approve_candidate(db: Session, song_id: int, candidate_id: int) -> Song | None:
    song = get_song(db, song_id)
    if song is None:
        return None
    cand = db.query(YouTubeCandidate).filter(
        YouTubeCandidate.id == candidate_id,
        YouTubeCandidate.song_id == song_id,
    ).one_or_none()
    if cand is None:
        return None
    song.selected_youtube_title = cand.title
    song.selected_youtube_channel = cand.channel
    song.selected_youtube_url = cand.url
    song.confidence_score = cand.confidence_score
    song.status = SongStatus.APPROVED
    db.add(LogEntry(
        song_id=song.id,
        level="INFO",
        message=f"User approved candidate #{cand.rank} ({cand.title}) at confidence {cand.confidence_score}",
    ))
    db.commit()
    return song


def skip_song(db: Session, song_id: int, reason: str | None = None) -> Song | None:
    song = get_song(db, song_id)
    if song is None:
        return None
    song.status = SongStatus.SKIPPED_LOW_CONFIDENCE
    if reason:
        song.notes = reason
    db.add(LogEntry(song_id=song.id, level="INFO", message=f"User skipped song. {reason or ''}".strip()))
    db.commit()
    return song


def mark_for_retry(db: Session, song_id: int) -> Song | None:
    from pathlib import Path
    song = get_song(db, song_id)
    if song is None:
        return None
    song.retry_count = (song.retry_count or 0) + 1
    song.notes = None

    # If the audio file is already on disk, the song only needs to be re-uploaded —
    # keep the YouTube selection and set APPROVED so the runner skips search/download.
    local_file_ok = bool(song.local_file_path and Path(song.local_file_path).exists())
    if local_file_ok and song.selected_youtube_url:
        song.status = SongStatus.APPROVED
    else:
        # No local file — full retry from search.
        song.status = SongStatus.PENDING
        song.selected_youtube_title = None
        song.selected_youtube_channel = None
        song.selected_youtube_url = None
        song.confidence_score = None

    db.add(LogEntry(song_id=song.id, level="INFO", message=f"User requested retry (count={song.retry_count})"))
    db.commit()
    return song
