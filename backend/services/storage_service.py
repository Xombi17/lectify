"""Object storage abstraction.

Two implementations:
  - LocalStorage  → writes files to STORAGE_LOCAL_DIR (preview + dev)
  - S3Storage     → S3-compatible (MinIO, R2, AWS, Emergent if configured)

Swap by setting STORAGE_BACKEND=local|s3 in .env. Routes/services only see
this `StorageService` interface.
"""
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from core.config import get_settings

settings = get_settings()


class StorageService(ABC):
    @abstractmethod
    async def save(self, key: str, fileobj: BinaryIO, content_type: str) -> str:
        """Save a file under `key`. Returns the storage key."""

    @abstractmethod
    def local_path(self, key: str) -> Path:
        """Return a local filesystem path for downstream processing (Gemini upload)."""

    @abstractmethod
    def public_url(self, key: str) -> str:
        """Return a URL the frontend can use to GET the file."""


class LocalStorage(StorageService):
    def __init__(self, root: str, public_base: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_base = public_base.rstrip("/")

    async def save(self, key: str, fileobj: BinaryIO, content_type: str) -> str:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as out:
            shutil.copyfileobj(fileobj, out)
        return key

    def local_path(self, key: str) -> Path:
        return self.root / key

    def public_url(self, key: str) -> str:
        return f"{self.public_base}/{key}"


def get_storage() -> StorageService:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorage(settings.STORAGE_LOCAL_DIR, settings.STORAGE_PUBLIC_BASE)
    # Future: return S3Storage(...) wired via boto3 + endpoint env vars
    raise RuntimeError(f"Unsupported STORAGE_BACKEND={settings.STORAGE_BACKEND}")
