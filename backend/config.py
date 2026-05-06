from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    APP_NAME: str = "Playlist Drive Uploader"
    GOOGLE_DRIVE_ROOT_FOLDER_NAME: str = "Playlist 3"
    LOCAL_TEMP_DOWNLOAD_FOLDER: str = "backend/temp_downloads"
    DATABASE_URL: str = "sqlite:///./playlist.db"
    AUTO_APPROVE_CONFIDENCE: int = 85
    MANUAL_REVIEW_CONFIDENCE: int = 70
    MAX_RETRIES: int = 2
    GOOGLE_CREDENTIALS_FILE: str = "credentials.json"
    GOOGLE_TOKEN_FILE: str = "token.json"
    AUDIO_PROVIDER: str = "ytdlp"
    FFMPEG_LOCATION: str = ""
    YTDLP_TIMEOUT_SECONDS: int = 600

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def temp_download_dir(self) -> Path:
        p = (PROJECT_ROOT / self.LOCAL_TEMP_DOWNLOAD_FOLDER).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def screenshots_dir(self) -> Path:
        p = (PROJECT_ROOT / "backend" / "screenshots").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def logs_dir(self) -> Path:
        p = (PROJECT_ROOT / "backend" / "logs").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def credentials_path(self) -> Path:
        return (PROJECT_ROOT / self.GOOGLE_CREDENTIALS_FILE).resolve()

    @property
    def token_path(self) -> Path:
        return (PROJECT_ROOT / self.GOOGLE_TOKEN_FILE).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
