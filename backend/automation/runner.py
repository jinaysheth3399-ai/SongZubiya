"""End-to-end runner: searches YouTube, scores candidates, processes audio,
verifies the file, and uploads to Drive.

Designed to be safely re-run after a crash:
- skips songs already in a terminal status
- saves progress after every song
- respects MAX_RETRIES per song
- reuses an existing Drive file (by drive_file_id or filename) instead of re-uploading
"""
from __future__ import annotations

import re
import threading
import traceback
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.models import (
    LogEntry,
    Playlist,
    Song,
    SongStatus,
    TERMINAL_STATUSES,
    YouTubeCandidate,
)
from backend.automation.youtube_search import search_youtube, CandidateData
from backend.automation.audio_processor import get_provider
from backend.verification.match_scoring import calculate_match_score
from backend.verification.file_verification import verify_audio_file
from backend.drive.uploader import upload_audio_file
from backend.drive.folders import ensure_root_folder, ensure_playlist_folder


# ---------------------------------------------------------------------------
# Global runner state (single-process)
# ---------------------------------------------------------------------------
class _RunnerState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self.is_running = False
        self.is_paused = False

    def start(self, target) -> bool:
        with self._lock:
            if self.is_running:
                return False
            self._stop_event.clear()
            self._pause_event.clear()
            self.is_running = True
            self.is_paused = False
            self._thread = threading.Thread(target=target, daemon=True)
            self._thread.start()
            return True

    def pause(self) -> None:
        self._pause_event.set()
        self.is_paused = True

    def resume(self) -> None:
        self._pause_event.clear()
        self.is_paused = False

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.clear()

    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    def wait_if_paused(self) -> None:
        while self._pause_event.is_set() and not self._stop_event.is_set():
            self._pause_event.wait(0.5)

    def mark_finished(self) -> None:
        with self._lock:
            self.is_running = False
            self.is_paused = False
            self._thread = None


runner_state = _RunnerState()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def sanitize_filename(track_no: str, song_name: str, artist: str) -> str:
    base = f"{track_no} - {song_name} - {artist}"
    cleaned = INVALID_FILENAME_CHARS.sub("_", base)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > 180:
        cleaned = cleaned[:180].rstrip()
    return f"{cleaned}.mp3"


def _log(db: Session, song_id: Optional[int], level: str, message: str) -> None:
    db.add(LogEntry(song_id=song_id, level=level, message=message))
    db.commit()


def _set_status(db: Session, song: Song, status: str, notes: Optional[str] = None) -> None:
    song.status = status
    if notes is not None:
        song.notes = notes
    db.commit()


# ---------------------------------------------------------------------------
# Per-song pipeline steps
# ---------------------------------------------------------------------------
def _search_and_score(db: Session, song: Song) -> Optional[YouTubeCandidate]:
    """Search YouTube, store candidates, pick the best one. Returns the chosen candidate."""
    _set_status(db, song, SongStatus.SEARCHING)

    # Wipe previous candidates so a retry starts fresh.
    for c in list(song.candidates):
        db.delete(c)
    db.commit()

    query = song.search_query or f"{song.song_name} {song.artist}"
    try:
        candidates: list[CandidateData] = search_youtube(
            query, max_results=5, screenshots_dir=settings.screenshots_dir
        )
    except Exception as exc:  # noqa: BLE001
        _log(db, song.id, "ERROR", f"YouTube search crashed: {exc}")
        return None

    if not candidates:
        _log(db, song.id, "WARNING", f"No YouTube results for query {query!r}")
        return None

    scored: list[tuple[int, CandidateData]] = []
    for cand in candidates:
        score = calculate_match_score(
            expected_song=song.song_name,
            expected_artist=song.artist,
            youtube_title=cand.title,
            channel_name=cand.channel,
            duration=cand.duration,
        )
        scored.append((score, cand))

    # Persist all candidates with their scores, sorted high -> low
    scored.sort(key=lambda x: x[0], reverse=True)
    chosen_db: Optional[YouTubeCandidate] = None
    for rank, (score, cand) in enumerate(scored, start=1):
        row = YouTubeCandidate(
            song_id=song.id,
            title=cand.title,
            channel=cand.channel,
            url=cand.url,
            duration=cand.duration,
            thumbnail_url=cand.thumbnail_url,
            confidence_score=score,
            rank=rank,
        )
        db.add(row)
        if rank == 1:
            chosen_db = row
    db.commit()
    return chosen_db


def _decide_after_search(db: Session, song: Song, chosen: YouTubeCandidate) -> bool:
    """Apply confidence thresholds. Returns True if processing should continue."""
    score = chosen.confidence_score or 0
    song.confidence_score = score
    song.selected_youtube_title = chosen.title
    song.selected_youtube_channel = chosen.channel
    song.selected_youtube_url = chosen.url

    if score >= settings.AUTO_APPROVE_CONFIDENCE:
        _set_status(db, song, SongStatus.APPROVED)
        _log(db, song.id, "INFO", f"Auto-approved at confidence {score}")
        return True

    if score >= settings.MANUAL_REVIEW_CONFIDENCE:
        _set_status(db, song, SongStatus.NEEDS_REVIEW)
        _log(db, song.id, "INFO", f"Awaiting manual review at confidence {score}")
        return False

    _set_status(db, song, SongStatus.SKIPPED_LOW_CONFIDENCE)
    _log(db, song.id, "WARNING", f"Skipped at low confidence {score}")
    return False


def _process_audio(db: Session, song: Song) -> Optional[Path]:
    _set_status(db, song, SongStatus.PROCESSING_AUDIO)
    target_filename = sanitize_filename(song.track_no, song.song_name, song.artist)
    target_path = settings.temp_download_dir / target_filename

    provider = get_provider()
    try:
        result = provider.fetch(
            song=song,
            verified_url=song.selected_youtube_url,
            target_path=target_path,
            log=lambda message: _log(db, song.id, "INFO", message),
        )
    except Exception as exc:  # noqa: BLE001
        _log(db, song.id, "ERROR", f"Audio provider crashed: {exc}\n{traceback.format_exc()}")
        _set_status(db, song, SongStatus.FAILED_AUDIO, notes=str(exc))
        return None

    if not result.success or not result.file_path:
        _log(db, song.id, "ERROR", f"Audio provider failed: {result.error}")
        _set_status(db, song, SongStatus.FAILED_AUDIO, notes=result.error or "Unknown audio error")
        return None

    song.local_file_path = str(result.file_path)
    db.commit()
    return Path(result.file_path)


def _verify_file(db: Session, song: Song, file_path: Path) -> bool:
    _set_status(db, song, SongStatus.VERIFYING_FILE)
    res = verify_audio_file(file_path)
    if not res.ok:
        _log(db, song.id, "ERROR", f"File verification failed: {res.reason}")
        _set_status(db, song, SongStatus.FAILED_VERIFICATION, notes=res.reason)
        return False
    return True


def _resolve_root_id(playlist: Playlist, cache: dict[str, str]) -> str:
    """Find/create the Drive root folder for this playlist's group."""
    root_name = (playlist.drive_root_name or settings.GOOGLE_DRIVE_ROOT_FOLDER_NAME).strip()
    if root_name not in cache:
        cache[root_name] = ensure_root_folder(root_name)
    return cache[root_name]


def _upload(db: Session, song: Song, file_path: Path, root_cache: dict[str, str]) -> bool:
    _set_status(db, song, SongStatus.UPLOADING)
    playlist: Playlist = song.playlist
    try:
        drive_root_id = _resolve_root_id(playlist, root_cache)
        playlist_folder_id = ensure_playlist_folder(playlist.name, drive_root_id)
        if playlist.drive_folder_id != playlist_folder_id:
            playlist.drive_folder_id = playlist_folder_id
            db.commit()

        # Skip duplicate upload if we already have a Drive file for this song.
        if song.drive_file_id and song.drive_web_link:
            _log(db, song.id, "INFO", "Drive file already recorded; reusing existing link.")
            _set_status(db, song, SongStatus.COMPLETED)
            return True

        upload_result = upload_audio_file(
            file_path=file_path,
            parent_folder_id=playlist_folder_id,
            filename=file_path.name,
        )
        song.drive_file_id = upload_result.file_id
        song.drive_web_link = upload_result.web_link
        db.commit()
        _log(
            db,
            song.id,
            "INFO",
            f"Uploaded to Drive: {upload_result.web_link} "
            f"({'reused existing' if upload_result.reused_existing else 'new upload'})",
        )
        _set_status(db, song, SongStatus.COMPLETED)
        return True
    except Exception as exc:  # noqa: BLE001
        _log(db, song.id, "ERROR", f"Drive upload failed: {exc}\n{traceback.format_exc()}")
        _set_status(db, song, SongStatus.FAILED_UPLOAD, notes=str(exc))
        return False


def _process_song(db: Session, song: Song, root_cache: dict[str, str]) -> None:
    """Run the full pipeline for one song, honoring its current status."""
    runner_state.wait_if_paused()
    if runner_state.should_stop():
        return

    # If we don't yet have a chosen YouTube URL, search.
    if not song.selected_youtube_url or song.status in (SongStatus.PENDING, SongStatus.FAILED_NO_RESULT):
        chosen = _search_and_score(db, song)
        if chosen is None:
            _set_status(db, song, SongStatus.FAILED_NO_RESULT, notes="No YouTube results")
            return
        if not _decide_after_search(db, song, chosen):
            return  # awaiting manual review or skipped

    # Status should now be APPROVED (auto or manual). Continue.
    if song.status != SongStatus.APPROVED:
        return

    runner_state.wait_if_paused()
    if runner_state.should_stop():
        return

    # Skip re-download if the audio is already on disk (e.g. Drive upload retry).
    existing = Path(song.local_file_path) if song.local_file_path else None
    if existing and existing.exists():
        file_path = existing
        _set_status(db, song, SongStatus.VERIFYING_FILE)
    else:
        file_path = _process_audio(db, song)
        if file_path is None:
            return

    if not _verify_file(db, song, file_path):
        return

    runner_state.wait_if_paused()
    if runner_state.should_stop():
        return

    _upload(db, song, file_path, root_cache)


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------
def _run_all() -> None:
    """Background thread entrypoint."""
    db: Session = SessionLocal()
    root_cache: dict[str, str] = {}
    try:
        # Pull songs to process: anything not in a terminal status, ordered by playlist + track.
        songs = (
            db.query(Song)
            .order_by(Song.playlist_id, Song.track_no, Song.id)
            .all()
        )

        for song in songs:
            if runner_state.should_stop():
                break

            # Skip terminal/completed songs unless they're explicitly requeued.
            if song.status in TERMINAL_STATUSES and song.status != SongStatus.FAILED_NO_RESULT:
                # COMPLETED stays. Failures stay until user retries.
                if song.status == SongStatus.COMPLETED:
                    continue
                # SKIPPED + other failures stay too unless retried via API.
                continue

            # Manual-review songs are paused until user approves a candidate.
            if song.status == SongStatus.NEEDS_REVIEW:
                continue

            # Bail out if retry budget exceeded.
            if song.retry_count > settings.MAX_RETRIES:
                _log(db, song.id, "WARNING", f"Retry budget exhausted ({song.retry_count})")
                continue

            try:
                _process_song(db, song, root_cache)
            except Exception as exc:  # noqa: BLE001
                _log(db, song.id, "ERROR", f"Unhandled error: {exc}\n{traceback.format_exc()}")
                song.notes = str(exc)
                db.commit()

        _log(db, None, "INFO", "Runner finished.")
    finally:
        db.close()
        runner_state.mark_finished()


def start_runner() -> bool:
    return runner_state.start(_run_all)


def pause_runner() -> None:
    runner_state.pause()


def resume_runner() -> None:
    runner_state.resume()


def stop_runner() -> None:
    runner_state.stop()


def runner_status() -> dict:
    return {
        "is_running": runner_state.is_running,
        "is_paused": runner_state.is_paused,
    }


def process_single_song(song_id: int) -> None:
    """Run the pipeline for a single approved/manual-reviewed song.

    Called after a user approves a candidate or retries a failure. Runs
    inline (not in a background thread) so the API call returns when done —
    callers should consider running this on a thread pool if responsiveness
    matters.
    """
    db: Session = SessionLocal()
    root_cache: dict[str, str] = {}
    try:
        song = db.query(Song).filter(Song.id == song_id).one_or_none()
        if song is None:
            return
        _process_song(db, song, root_cache)
    finally:
        db.close()
