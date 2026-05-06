from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.database import Base


# Status string constants
class SongStatus:
    PENDING = "Pending"
    SEARCHING = "Searching YouTube"
    NEEDS_REVIEW = "Needs Manual Review"
    APPROVED = "Approved"
    PROCESSING_AUDIO = "Processing Audio"
    VERIFYING_FILE = "Verifying File"
    UPLOADING = "Uploading to Drive"
    COMPLETED = "Completed"
    SKIPPED_LOW_CONFIDENCE = "Skipped - Low Confidence"
    FAILED_NO_RESULT = "Failed - No Result"
    FAILED_AUDIO = "Failed - Audio Processing Error"
    FAILED_VERIFICATION = "Failed - File Verification Error"
    FAILED_UPLOAD = "Failed - Drive Upload Error"


TERMINAL_STATUSES = {
    SongStatus.COMPLETED,
    SongStatus.SKIPPED_LOW_CONFIDENCE,
    SongStatus.FAILED_NO_RESULT,
    SongStatus.FAILED_AUDIO,
    SongStatus.FAILED_VERIFICATION,
    SongStatus.FAILED_UPLOAD,
}


class Playlist(Base):
    __tablename__ = "playlists"
    __table_args__ = (
        UniqueConstraint("drive_root_name", "name", name="uq_playlists_root_name"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    drive_folder_id = Column(String, nullable=True)
    drive_root_name = Column(String, nullable=True)  # Drive root folder; falls back to env default
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    songs = relationship("Song", back_populates="playlist", cascade="all,delete-orphan")


class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False)
    track_no = Column(String, nullable=False)
    song_name = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    search_query = Column(String, nullable=True)

    selected_youtube_title = Column(String, nullable=True)
    selected_youtube_channel = Column(String, nullable=True)
    selected_youtube_url = Column(String, nullable=True)

    confidence_score = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default=SongStatus.PENDING)

    local_file_path = Column(String, nullable=True)
    drive_file_id = Column(String, nullable=True)
    drive_web_link = Column(String, nullable=True)

    retry_count = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    playlist = relationship("Playlist", back_populates="songs")
    candidates = relationship(
        "YouTubeCandidate",
        back_populates="song",
        cascade="all,delete-orphan",
        order_by="YouTubeCandidate.rank",
    )
    logs = relationship("LogEntry", back_populates="song", cascade="all,delete-orphan")


class YouTubeCandidate(Base):
    __tablename__ = "youtube_candidates"

    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    title = Column(String, nullable=True)
    channel = Column(String, nullable=True)
    url = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    rank = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    song = relationship("Song", back_populates="candidates")


class LogEntry(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    level = Column(String, nullable=False, default="INFO")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    song = relationship("Song", back_populates="logs")
