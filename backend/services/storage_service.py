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

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_PRESIGN_SECONDS = 900



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

    @abstractmethod
    async def presign_post(self, key: str, content_type: str, max_bytes: int = 200*1024*1024, expires: int = 900) -> dict:
        """Return {"url": str, "fields": dict} for browser-direct POST."""

    @abstractmethod
    async def presign_get(self, key: str, expires: int = 900) -> str:
        """Return a presigned GET URL string."""

    @abstractmethod
    async def head_object(self, key: str) -> dict:
        """Return {"size": int, "content_type": str}; raises FileNotFoundError if absent."""


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

    async def presign_post(self, key: str, content_type: str, max_bytes: int = 200*1024*1024, expires: int = 900) -> dict:
        raise NotImplementedError("presign_post not supported by LocalStorage")

    async def presign_get(self, key: str, expires: int = 900) -> str:
        raise NotImplementedError("presign_get not supported by LocalStorage")

    async def head_object(self, key: str) -> dict:
        p = self._path(key)
        if not p.exists():
            raise FileNotFoundError(f"Storage key not found: {key}")
        return {"size": p.stat().st_size, "content_type": "application/octet-stream"}


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
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        import aioboto3  # lazy import so dev envs don't need it

        self.bucket = bucket
        kwargs = {"region_name": region}
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
            
        self._session = aioboto3.Session(**kwargs)
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
        # Probe metadata first (head_object on its own short-lived client)
        async with self._client() as s3:
            head = await s3.head_object(Bucket=self.bucket, Key=key)
        size = head.get("ContentLength")
        ctype = head.get("ContentType") or "application/octet-stream"

        bucket = self.bucket
        chunk_size = self.CHUNK_BYTES
        client_factory = self._client

        async def _iter() -> AsyncIterator[bytes]:
            # CRITICAL: keep the client + response open until iteration completes.
            async with client_factory() as s3:
                obj = await s3.get_object(Bucket=bucket, Key=key)
                async for chunk in obj["Body"].iter_chunks(chunk_size):
                    yield chunk

        return _iter(), size, ctype

    async def delete(self, key: str) -> None:
        try:
            async with self._client() as s3:
                await s3.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            return  # best-effort

    async def presign_post(self, key: str, content_type: str, max_bytes: int = 200*1024*1024, expires: int = 900) -> dict:
        max_bytes = min(max_bytes, MAX_UPLOAD_BYTES)
        expires = min(expires, MAX_PRESIGN_SECONDS)
        async with self._client() as s3:
            return await s3.generate_presigned_post(
                Bucket=self.bucket,
                Key=key,
                Fields={"Content-Type": content_type},
                Conditions=[
                    ["content-length-range", 1, max_bytes],
                    {"Content-Type": content_type},
                ],
                ExpiresIn=expires,
            )

    async def presign_get(self, key: str, expires: int = 900) -> str:
        expires = min(expires, MAX_PRESIGN_SECONDS)
        async with self._client() as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires,
            )

    async def head_object(self, key: str) -> dict:
        from botocore.exceptions import ClientError
        try:
            async with self._client() as s3:
                head = await s3.head_object(Bucket=self.bucket, Key=key)
                return {
                    "size": head.get("ContentLength", 0),
                    "content_type": head.get("ContentType", "application/octet-stream"),
                }
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                raise FileNotFoundError(key)
            raise


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
            access_key=os.environ.get("OBJECT_STORAGE_ACCESS_KEY") or None,
            secret_key=os.environ.get("OBJECT_STORAGE_SECRET_KEY") or None,
        )
    raise RuntimeError(f"Unsupported STORAGE_BACKEND={backend!r}")
