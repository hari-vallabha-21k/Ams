import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import settings

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_EXTENSIONS = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


def safe_file_name(name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", Path(name).name).strip("._") or "document"
    return cleaned[:120]


def save_upload(upload: UploadFile, subject_type: str, subject_id: int) -> tuple[str, int, str]:
    """Validate and store an uploaded document outside the database.

    Returns (stored_path, size_bytes, safe_file_name).
    """
    mime = (upload.content_type or "").lower()
    if mime not in settings.allowed_mime_list:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{mime or 'unknown'}'. Allowed: {settings.allowed_mime_types}",
        )

    contents = upload.file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit",
        )

    directory = Path(settings.storage_dir) / subject_type.lower() / str(subject_id)
    directory.mkdir(parents=True, exist_ok=True)
    extension = _EXTENSIONS.get(mime, Path(upload.filename or "").suffix or "")
    stored = directory / f"{uuid.uuid4().hex}{extension}"
    with open(stored, "wb") as handle:
        handle.write(contents)
    os.chmod(stored, 0o640)
    return str(stored), len(contents), safe_file_name(upload.filename or f"document{extension}")
