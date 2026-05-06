"""Local audio file sanity checks before Drive upload."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile  # type: ignore


VALID_EXTENSIONS = {".mp3", ".m4a", ".wav"}
MIN_FILE_SIZE_BYTES = 500 * 1024  # 500 KB
MIN_DURATION_SECONDS = 60
MAX_DURATION_SECONDS = 15 * 60


@dataclass
class VerificationResult:
    ok: bool
    reason: str | None = None
    duration_seconds: float | None = None
    size_bytes: int | None = None


def verify_audio_file(file_path: str | Path) -> VerificationResult:
    path = Path(file_path)
    if not path.exists():
        return VerificationResult(False, "File does not exist")

    size = path.stat().st_size
    if size < MIN_FILE_SIZE_BYTES:
        return VerificationResult(False, f"File too small ({size} bytes)", size_bytes=size)

    if path.suffix.lower() not in VALID_EXTENSIONS:
        return VerificationResult(
            False,
            f"Invalid extension {path.suffix!r}; expected one of {sorted(VALID_EXTENSIONS)}",
            size_bytes=size,
        )

    duration: float | None = None
    try:
        mf = MutagenFile(str(path))
        if mf is not None and getattr(mf, "info", None) is not None:
            duration = float(mf.info.length)
    except Exception as exc:  # noqa: BLE001
        return VerificationResult(False, f"Metadata read failed: {exc}", size_bytes=size)

    if duration is not None:
        if duration < MIN_DURATION_SECONDS or duration > MAX_DURATION_SECONDS:
            return VerificationResult(
                False,
                f"Duration {duration:.1f}s outside allowed range "
                f"[{MIN_DURATION_SECONDS}-{MAX_DURATION_SECONDS}]",
                duration_seconds=duration,
                size_bytes=size,
            )

    return VerificationResult(True, None, duration_seconds=duration, size_bytes=size)
