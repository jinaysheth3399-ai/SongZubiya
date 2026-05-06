"""Google Drive OAuth — uses ``credentials.json`` and caches in ``token.json``.

First call opens a browser for consent. Subsequent calls reuse the cached token.
"""
from __future__ import annotations

import ssl
import time
import threading
from typing import Callable, Optional, TypeVar

T = TypeVar("T")

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from backend.config import settings


SCOPES = ["https://www.googleapis.com/auth/drive.file"]

_lock = threading.Lock()
_cached_service: Optional[Resource] = None


def _load_credentials() -> Credentials:
    creds: Optional[Credentials] = None
    token_path = settings.token_path
    creds_path = settings.credentials_path

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except Exception:
            creds = None  # fall through to fresh auth

    if not creds_path.exists():
        raise FileNotFoundError(
            f"Google OAuth credentials not found at {creds_path}. "
            f"Place your OAuth Desktop credentials.json in the project root."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    # run_local_server opens the browser, listens on a free port, exchanges the code.
    creds = flow.run_local_server(port=0, prompt="consent")
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def get_drive_service() -> Resource:
    global _cached_service
    with _lock:
        if _cached_service is not None:
            return _cached_service
        creds = _load_credentials()
        _cached_service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return _cached_service


def reset_service_cache() -> None:
    """Force the next call to rebuild the service (e.g. after re-auth)."""
    global _cached_service
    with _lock:
        _cached_service = None


_SSL_MARKERS = ("SSL", "ssl", "WRONG_VERSION", "DECRYPTION_FAILED", "BAD_RECORD_MAC", "ConnectionReset")


def with_ssl_retry(fn: Callable[[], T], retries: int = 4, base_delay: float = 1.5) -> T:
    """Call fn(), retrying on SSL/transport errors with exponential back-off.

    On each SSL failure the service cache is reset so the next attempt gets a
    fresh HTTP connection pool — this is the only reliable way to recover from
    a corrupted TLS session.
    """
    for attempt in range(retries + 1):
        try:
            return fn()
        except ssl.SSLError:
            if attempt == retries:
                raise
            reset_service_cache()
            time.sleep(base_delay * (2 ** attempt))
        except Exception as exc:
            if attempt < retries and any(m in str(exc) for m in _SSL_MARKERS):
                reset_service_cache()
                time.sleep(base_delay * (2 ** attempt))
                continue
            raise
    raise RuntimeError("unreachable")
