"""Object storage abstraction.

Two implementations:
  - LocalStorage  → writes files under STORAGE_LOCAL_DIR (preview + tests)
  - S3Storage     → S3-compatible (MinIO, Cloudflare R2, AWS S3) via aioboto3

Configuration is read from env in `get_storage()`. Routes/services only
ever see the `StorageService` interface — they never touch boto3 or the
local filesystem directly.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, BinaryIO

from core.config import get_settings

settings = get_settings()


class StorageService(ABC):
    """Backend-agnostic blob storage.

    The unit of work is a `key` (e.g. `lectures/<id>/audio.mp3`).
    """

    @abstractmethod
    async def save(self, key: str, fileobj: BinaryIO, content_type: str) -> str:
        """Persist `fileobj` under `key`. Returns `key`."""

    @abstractmethod
    def open_local(self, key: str) -> AbstractAsyncContextManager[Path]:
        """Return an async context manager yielding a local filesystem Path.

        For LocalStorage, no-op (the file already lives on disk).
        For S3Storage, downloads to a temp file and cleans up on exit.

        Usage:
            async with storage.open_local(key) as path:
                ...
        """

    @abstractmethod
    async def stream(self, key: str) -> tuple[AsyncIterator[bytes], int | None, str]:
        """Return (async byte-iterator, content-length-or-None, content-type)."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Best-effort delete; never raises on missing keys."""


# --------------------------------------------------------------------------
# Local filesystem implementation
# --------------------------------------------------------------------------
class LocalStorage(StorageService):
    CHUNK_BYTES = 1024 * 1024  # 1 MB

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # prevent path traversal
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError(f"Refusing path-traversal key: {key!r}")
        return p

    def local_path(self, key: str) -> Path:
        """Concrete LocalStorage helper (not on the abstract interface).

        Useful for test seeding and any code that knows it's running against
        a local backend. Production code should prefer `open_local()` so it
        works with S3 too.
        """
        return self._path(key)

    async def save(self, key: str, fileobj: BinaryIO, content_type: str) -> str:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        # shutil.copyfileobj is blocking; run in thread to avoid stalling the loop
        await asyncio.to_thread(_copy_to_disk, fileobj, target)
        return key

    @asynccontextmanager
    async def open_local(self, key: str) -> AsyncIterator[Path]:
        p = self._path(key)
        if not p.exists():
            raise FileNotFoundError(f"Storage key not found: {key}")
        yield p  # nothing to clean up

    async def stream(self, key: str) -> tuple[AsyncIterator[bytes], int | None, str]:
        p = self._path(key)
        if not p.exists():
            raise FileNotFoundError(key)
        size = p.stat().st_size
        return _file_iter(p, self.CHUNK_BYTES), size, "application/octet-stream"

    async def delete(self, key: str) -> None:
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            return
        except OSError:
            return


def _copy_to_disk(fileobj: BinaryIO, target: Path) -> None:
    with target.open("wb") as out:
        shutil.copyfileobj(fileobj, out)


async def _file_iter(path: Path, chunk: int) -> AsyncIterator[bytes]:
    # Read in a thread to keep the event loop free.
    def _read_chunk(fh):
        return fh.read(chunk)

    with path.open("rb") as fh:
        while True:
            data = await asyncio.to_thread(_read_chunk, fh)
            if not data:
                break
            yield data


# --------------------------------------------------------------------------
# S3 / S3-compatible implementation (MinIO, R2, AWS)
# --------------------------------------------------------------------------
class S3Storage(StorageService):
    CHUNK_BYTES = 1024 * 1024  # 1 MB

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None,
        region: str,
        access_key: str,
        secret_key: str,
    ):
        import aioboto3  # lazy import so dev envs don't need it

        self.bucket = bucket
        self._session = aioboto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        self._endpoint = endpoint_url or None

    def _client(self):
        return self._session.client("s3", endpoint_url=self._endpoint)

    async def save(self, key: str, fileobj: BinaryIO, content_type: str) -> str:
        async with self._client() as s3:
            await s3.upload_fileobj(
                fileobj,
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type or "application/octet-stream"},
            )
        return key

    @asynccontextmanager
    async def open_local(self, key: str) -> AsyncIterator[Path]:
        fd, tmp = tempfile.mkstemp(prefix="lecturemind_", suffix=Path(key).suffix)
        os.close(fd)
        tmp_path = Path(tmp)
        try:
            async with self._client() as s3:
                await s3.download_file(self.bucket, key, str(tmp_path))
            yield tmp_path
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass

    async def stream(self, key: str) -> tuple[AsyncIterator[bytes], int | None, str]:
        async with self._client() as s3:
            obj = await s3.get_object(Bucket=self.bucket, Key=key)
            body = obj["Body"]
            size = obj.get("ContentLength")
            ctype = obj.get("ContentType") or "application/octet-stream"

            async def _iter() -> AsyncIterator[bytes]:
                async for chunk in body.iter_chunks(self.CHUNK_BYTES):
                    yield chunk

            return _iter(), size, ctype

    async def delete(self, key: str) -> None:
        try:
            async with self._client() as s3:
                await s3.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            return  # best-effort


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------
def get_storage() -> StorageService:
    backend = (settings.STORAGE_BACKEND or "local").lower()
    if backend == "local":
        return LocalStorage(settings.STORAGE_LOCAL_DIR)
    if backend == "s3":
        bucket = os.environ.get("OBJECT_STORAGE_BUCKET")
        if not bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 requires OBJECT_STORAGE_BUCKET")
        return S3Storage(
            bucket=bucket,
            endpoint_url=os.environ.get("OBJECT_STORAGE_ENDPOINT") or None,
            region=os.environ.get("OBJECT_STORAGE_REGION", "us-east-1"),
            access_key=os.environ.get("OBJECT_STORAGE_ACCESS_KEY", ""),
            secret_key=os.environ.get("OBJECT_STORAGE_SECRET_KEY", ""),
        )
    raise RuntimeError(f"Unsupported STORAGE_BACKEND={backend!r}")
