"""Pluggable audio source/processor architecture.

Built-in providers:
- ``stub``  : safe placeholder that does nothing (fails clearly)
- ``ytdlp`` : downloads audio via yt-dlp + ffmpeg and converts to mp3

Select the active provider via the ``AUDIO_PROVIDER`` env var (default: ytdlp).
"""
from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.config import settings


@dataclass
class AudioFetchResult:
    success: bool
    file_path: Optional[Path] = None
    error: Optional[str] = None


class AudioProvider(ABC):
    name: str = ""

    @abstractmethod
    def fetch(self, song, verified_url: str, target_path: Path, log=None) -> AudioFetchResult:
        """Produce an audio file at target_path. Return success=False on expected failures."""


_REGISTRY: dict[str, AudioProvider] = {}


def register_provider(provider: AudioProvider) -> None:
    if not provider.name:
        raise ValueError("AudioProvider must define a non-empty `name`.")
    _REGISTRY[provider.name] = provider


def get_provider(name: str | None = None) -> AudioProvider:
    key = (name or settings.AUDIO_PROVIDER).strip().lower()
    if key not in _REGISTRY:
        raise RuntimeError(
            f"Audio provider {key!r} is not registered. "
            f"Available: {sorted(_REGISTRY.keys()) or '[none]'}."
        )
    return _REGISTRY[key]


# ---------------------------------------------------------------------------
# Stub provider
# ---------------------------------------------------------------------------
class StubAudioProvider(AudioProvider):
    name = "stub"

    def fetch(self, song, verified_url: str, target_path: Path, log=None) -> AudioFetchResult:
        return AudioFetchResult(
            success=False,
            error=(
                "Stub audio provider is active. Set AUDIO_PROVIDER=ytdlp in .env "
                "to actually fetch audio."
            ),
        )


register_provider(StubAudioProvider())


# ---------------------------------------------------------------------------
# yt-dlp provider (Python API — same approach that processed Playlist 3)
# ---------------------------------------------------------------------------
class YtDlpAudioProvider(AudioProvider):
    name = "ytdlp"

    @staticmethod
    def _clean_youtube_url(url: str) -> str:
        """Strip playlist/radio params so yt-dlp downloads exactly one video."""
        from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

        parts = urlsplit(url)
        if "youtube.com" not in parts.netloc and "youtu.be" not in parts.netloc:
            return url
        if "youtu.be" in parts.netloc:
            return urlunsplit((parts.scheme, "www.youtube.com", "/watch",
                               urlencode([("v", parts.path.lstrip("/"))]), ""))
        kept = [(k, v) for k, v in parse_qsl(parts.query) if k == "v"]
        if not kept:
            return url
        return urlunsplit((parts.scheme, parts.netloc, "/watch", urlencode(kept), ""))

    def fetch(self, song, verified_url: str, target_path: Path, log=None) -> AudioFetchResult:
        if not verified_url:
            return AudioFetchResult(success=False, error="No verified URL on song")

        verified_url = self._clean_youtube_url(verified_url)

        try:
            import yt_dlp  # type: ignore
        except ImportError:
            return AudioFetchResult(
                success=False,
                error="yt-dlp is not installed. Run: pip install -r requirements.txt",
            )

        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        ffmpeg_location = settings.FFMPEG_LOCATION.strip() or None
        if ffmpeg_location is None and shutil.which("ffmpeg") is None:
            return AudioFetchResult(
                success=False,
                error=(
                    "ffmpeg not found. Install ffmpeg and put it on PATH, "
                    "or set FFMPEG_LOCATION in .env."
                ),
            )

        out_stem = str(target_path.with_suffix(""))
        outtmpl = out_stem + ".%(ext)s"

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 3,
            "fragment_retries": 3,
            "concurrent_fragment_downloads": 1,
            "socket_timeout": 30,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                },
                {"key": "FFmpegMetadata"},
            ],
            "writethumbnail": False,
            "overwrites": True,
        }
        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([verified_url])
        except Exception as exc:  # noqa: BLE001
            return AudioFetchResult(success=False, error=f"yt-dlp failed: {exc}")

        produced = Path(out_stem + ".mp3")
        if not produced.exists():
            for candidate in target_path.parent.glob(target_path.stem + ".*"):
                if candidate.suffix.lower() in {".mp3", ".m4a", ".wav"}:
                    produced = candidate
                    break

        if not produced.exists():
            return AudioFetchResult(
                success=False,
                error=f"Expected audio file not found at {produced}",
            )

        if produced != target_path:
            try:
                if target_path.exists():
                    target_path.unlink()
                produced.rename(target_path)
            except Exception as exc:  # noqa: BLE001
                return AudioFetchResult(
                    success=False,
                    error=f"Could not rename produced file: {exc}",
                )

        return AudioFetchResult(success=True, file_path=target_path)


register_provider(YtDlpAudioProvider())
