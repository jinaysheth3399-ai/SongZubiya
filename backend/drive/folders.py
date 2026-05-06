"""Drive folder helpers — find/create root and per-playlist folders."""
from __future__ import annotations

from googleapiclient.errors import HttpError

from backend.drive.auth import get_drive_service, with_ssl_retry


FOLDER_MIME = "application/vnd.google-apps.folder"


def _escape_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def find_folder(name: str, parent_id: str | None = None) -> str | None:
    """Return the folder ID matching ``name`` under ``parent_id`` (or root)."""
    service = get_drive_service()
    safe = _escape_query(name)
    q_parts = [
        f"mimeType = '{FOLDER_MIME}'",
        f"name = '{safe}'",
        "trashed = false",
    ]
    if parent_id:
        q_parts.append(f"'{_escape_query(parent_id)}' in parents")
    query = " and ".join(q_parts)

    response = with_ssl_retry(lambda: service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=10,
    ).execute())
    files = response.get("files", [])
    return files[0]["id"] if files else None


def create_folder(name: str, parent_id: str | None = None) -> str:
    service = get_drive_service()
    body = {"name": name, "mimeType": FOLDER_MIME}
    if parent_id:
        body["parents"] = [parent_id]
    folder = with_ssl_retry(lambda: service.files().create(body=body, fields="id").execute())
    return folder["id"]


def ensure_root_folder(name: str) -> str:
    folder_id = find_folder(name, parent_id=None)
    if folder_id:
        return folder_id
    return create_folder(name, parent_id=None)


def ensure_playlist_folder(playlist_name: str, root_folder_id: str) -> str:
    folder_id = find_folder(playlist_name, parent_id=root_folder_id)
    if folder_id:
        return folder_id
    return create_folder(playlist_name, parent_id=root_folder_id)


def find_file_in_folder(filename: str, parent_id: str) -> dict | None:
    """Return {'id', 'webViewLink'} for an existing file with the given name."""
    service = get_drive_service()
    safe_name = _escape_query(filename)
    safe_parent = _escape_query(parent_id)
    query = (
        f"name = '{safe_name}' and "
        f"'{safe_parent}' in parents and "
        f"trashed = false and "
        f"mimeType != '{FOLDER_MIME}'"
    )
    try:
        response = with_ssl_retry(lambda: service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name, webViewLink)",
            pageSize=5,
        ).execute())
    except HttpError:
        return None
    files = response.get("files", [])
    return files[0] if files else None
