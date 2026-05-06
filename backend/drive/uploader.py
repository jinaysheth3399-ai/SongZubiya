"""Upload audio files to Drive with duplicate prevention + public-link permission."""
from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from backend.drive.auth import get_drive_service, with_ssl_retry
from backend.drive.folders import find_file_in_folder


@dataclass
class UploadResult:
    file_id: str
    web_link: str
    reused_existing: bool = False


def _ensure_anyone_with_link(service, file_id: str) -> None:
    """Idempotent: grant 'anyone with the link can view' if not already set."""
    try:
        perms = with_ssl_retry(lambda: service.permissions().list(
            fileId=file_id, fields="permissions(id,type,role)"
        ).execute())
        for p in perms.get("permissions", []):
            if p.get("type") == "anyone" and p.get("role") in ("reader", "commenter", "writer"):
                return
        with_ssl_retry(lambda: service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute())
    except HttpError:
        # Best-effort: if listing fails, just try to create.
        try:
            with_ssl_retry(lambda: service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
                fields="id",
            ).execute())
        except HttpError:
            pass


def _get_web_link(service, file_id: str) -> str:
    meta = with_ssl_retry(lambda: service.files().get(fileId=file_id, fields="id, webViewLink").execute())
    return meta.get("webViewLink", "")


def upload_audio_file(
    file_path: Path,
    parent_folder_id: str,
    filename: str,
) -> UploadResult:
    """Upload (or reuse) an audio file in Drive. Always sets anyone-with-link view.

    Duplicate prevention: if a file with the same name already exists in the
    target folder, that one is reused instead of re-uploading.
    """
    service = get_drive_service()

    existing = find_file_in_folder(filename, parent_folder_id)
    if existing:
        file_id = existing["id"]
        _ensure_anyone_with_link(service, file_id)
        web_link = existing.get("webViewLink") or _get_web_link(service, file_id)
        return UploadResult(file_id=file_id, web_link=web_link, reused_existing=True)

    mime, _ = mimetypes.guess_type(filename)
    if not mime:
        mime = "audio/mpeg"

    body = {"name": filename, "parents": [parent_folder_id]}
    media = MediaFileUpload(str(file_path), mimetype=mime, resumable=True)

    def _do_upload():
        svc = get_drive_service()
        req = svc.files().create(body=body, media_body=media, fields="id, webViewLink")
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        return resp

    response = with_ssl_retry(_do_upload)
    file_id = response["id"]
    web_link = response.get("webViewLink") or _get_web_link(service, file_id)

    _ensure_anyone_with_link(service, file_id)
    return UploadResult(file_id=file_id, web_link=web_link, reused_existing=False)


def test_drive_connection() -> dict:
    """Lightweight connectivity check used by /api/drive/test."""
    service = get_drive_service()
    about = service.about().get(fields="user(displayName,emailAddress), storageQuota").execute()
    return about
