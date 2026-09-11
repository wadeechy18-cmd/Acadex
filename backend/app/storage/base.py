"""Storage abstraction.

Upload/download code (endpoints, services) should depend only on this interface,
never on a specific provider SDK. This lets us start with local disk storage in
development and switch to S3-compatible object storage in production by changing
STORAGE_BACKEND, with no changes to callers.
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/plain",
}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm"}

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024
MAX_VIDEO_SIZE_BYTES = 2 * 1024 * 1024 * 1024


class StorageBackend(ABC):
    @abstractmethod
    def save(self, file_bytes: bytes, filename: str, content_type: str, folder: str) -> str:
        """Persist a file and return its storage key."""

    @abstractmethod
    def url_for(self, storage_key: str) -> str:
        """Return a URL the client can use to fetch the stored file."""

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Remove a stored file."""


def safe_filename(original_filename: str) -> str:
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: str, public_base_url: str = "") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.public_base_url = public_base_url.rstrip("/")

    def save(self, file_bytes: bytes, filename: str, content_type: str, folder: str) -> str:
        target_dir = self.base_path / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        key = f"{folder}/{safe_filename(filename)}"
        with open(self.base_path / key, "wb") as f:
            f.write(file_bytes)
        return key

    def url_for(self, storage_key: str) -> str:
        # Absolute, since the frontend is a separate origin from the API.
        return f"{self.public_base_url}/uploads/{storage_key}"

    def delete(self, storage_key: str) -> None:
        target = self.base_path / storage_key
        if target.exists():
            os.remove(target)


class S3StorageBackend(StorageBackend):
    """Placeholder for a future S3-compatible backend (AWS S3 / Cloudflare R2 /
    Backblaze B2). Implemented when a production storage provider is chosen;
    callers already depend only on the StorageBackend interface, so this can be
    filled in without touching any endpoint or service code.
    """

    def __init__(self, bucket: str, region: str | None, access_key: str | None,
                 secret_key: str | None, endpoint_url: str | None) -> None:
        raise NotImplementedError("S3 storage backend is not configured yet.")

    def save(self, file_bytes: bytes, filename: str, content_type: str, folder: str) -> str:
        raise NotImplementedError

    def url_for(self, storage_key: str) -> str:
        raise NotImplementedError

    def delete(self, storage_key: str) -> None:
        raise NotImplementedError


def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalStorageBackend(settings.storage_local_path, settings.public_base_url)
    return S3StorageBackend(
        bucket=settings.storage_s3_bucket or "",
        region=settings.storage_s3_region,
        access_key=settings.storage_s3_access_key,
        secret_key=settings.storage_s3_secret_key,
        endpoint_url=settings.storage_s3_endpoint_url,
    )
