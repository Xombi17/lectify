"""Storage abstraction tests: LocalStorage, S3Storage (via moto), get_storage()."""
import asyncio
import importlib
import io
import os
import sys
import tempfile

import pytest

sys.path.insert(0, "/app/backend")


def _arun(coro):
    return asyncio.run(coro)


def _reload_storage_module():
    """Reload config + storage_service so module-level `settings` re-reads env."""
    from core import config as cfg
    cfg.get_settings.cache_clear()
    importlib.reload(cfg)
    import services.storage_service as ss
    importlib.reload(ss)
    return ss


# ---------------------------------------------------------------------------
# LocalStorage
# ---------------------------------------------------------------------------
class TestLocalStorage:
    def _fresh(self):
        from services.storage_service import LocalStorage
        d = tempfile.mkdtemp(prefix="lm_local_")
        return LocalStorage(d), d

    def test_save_and_open_local_roundtrip(self):
        ls, _ = self._fresh()
        payload = b"hello-local-storage"

        async def go():
            await ls.save("foo/bar.bin", io.BytesIO(payload), "application/octet-stream")
            async with ls.open_local("foo/bar.bin") as p:
                assert p.exists()
                assert p.read_bytes() == payload
            assert ls.local_path("foo/bar.bin").read_bytes() == payload
        _arun(go())

    def test_stream_returns_iter_size_and_ctype(self):
        ls, _ = self._fresh()
        payload = b"x" * (1024 * 1024 + 17)

        async def go():
            await ls.save("a.bin", io.BytesIO(payload), "application/octet-stream")
            it, size, ctype = await ls.stream("a.bin")
            assert size == len(payload)
            assert ctype == "application/octet-stream"
            collected = b""
            async for chunk in it:
                collected += chunk
            assert collected == payload
        _arun(go())

    def test_delete_is_best_effort(self):
        ls, _ = self._fresh()

        async def go():
            await ls.save("g.txt", io.BytesIO(b"x"), "text/plain")
            await ls.delete("g.txt")
            await ls.delete("g.txt")  # second delete must not raise
            with pytest.raises(FileNotFoundError):
                async with ls.open_local("g.txt"):
                    pass
        _arun(go())

    def test_path_traversal_rejected(self):
        ls, _ = self._fresh()

        async def go():
            with pytest.raises(ValueError):
                await ls.save("../etc/passwd", io.BytesIO(b"oops"), "text/plain")
        _arun(go())


# ---------------------------------------------------------------------------
# get_storage() factory
# ---------------------------------------------------------------------------
class TestStorageFactory:
    def teardown_method(self, _):
        os.environ["STORAGE_BACKEND"] = "local"
        os.environ.pop("OBJECT_STORAGE_BUCKET", None)
        _reload_storage_module()

    def test_local_backend(self, monkeypatch):
        monkeypatch.setenv("STORAGE_BACKEND", "local")
        ss = _reload_storage_module()
        s = ss.get_storage()
        assert isinstance(s, ss.LocalStorage)

    def test_s3_missing_bucket_raises(self, monkeypatch):
        monkeypatch.setenv("STORAGE_BACKEND", "s3")
        monkeypatch.delenv("OBJECT_STORAGE_BUCKET", raising=False)
        ss = _reload_storage_module()
        with pytest.raises(RuntimeError, match="OBJECT_STORAGE_BUCKET"):
            ss.get_storage()

    def test_unknown_backend_raises(self, monkeypatch):
        monkeypatch.setenv("STORAGE_BACKEND", "weirdfs")
        ss = _reload_storage_module()
        with pytest.raises(RuntimeError, match="Unsupported"):
            ss.get_storage()

    def test_s3_keyless(self, monkeypatch):
        monkeypatch.setenv("STORAGE_BACKEND", "s3")
        monkeypatch.setenv("OBJECT_STORAGE_BUCKET", "mybucket")
        monkeypatch.delenv("OBJECT_STORAGE_ACCESS_KEY", raising=False)
        monkeypatch.delenv("OBJECT_STORAGE_SECRET_KEY", raising=False)
        
        class MockSession:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                
        import aioboto3
        monkeypatch.setattr(aioboto3, "Session", MockSession)
        
        ss = _reload_storage_module()
        s = ss.get_storage()
        assert "aws_access_key_id" not in s._session.kwargs
        assert "aws_secret_access_key" not in s._session.kwargs


# ---------------------------------------------------------------------------
# S3Storage via moto (mock_aws)
#
# NOTE: aioboto3 2.25 + moto 5.x has a known issue with chunked
# Transfer-Encoding on `upload_fileobj` (moto's S3 handler can't decode the
# coroutine body). We therefore seed objects via the sync boto3 client (which
# does NOT use chunked encoding) and exercise the read/delete codepaths of
# S3Storage against them. The aioboto3 *put* codepath is structurally a
# direct passthrough to upload_fileobj and is not unit-testable against moto
# at present; it is covered by docker-compose smoke-test against real MinIO.
# ---------------------------------------------------------------------------
class TestS3Storage:
    BUCKET = "lecturemind-test"

    @pytest.fixture(autouse=True)
    def _moto_server(self):
        """Spin up an in-process moto server so aioboto3 can hit a real HTTP endpoint."""
        from moto.server import ThreadedMotoServer
        server = ThreadedMotoServer(port=0)
        server.start()
        host, port = server.get_host_and_port()
        self.endpoint = f"http://{host}:{port}"
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        # create bucket via sync boto3 client against the moto server
        import boto3
        boto3.client(
            "s3", endpoint_url=self.endpoint, region_name="us-east-1",
            aws_access_key_id="testing", aws_secret_access_key="testing",
        ).create_bucket(Bucket=self.BUCKET)
        yield
        server.stop()

    def _seed(self, key, body, ctype="application/octet-stream"):
        import boto3
        boto3.client(
            "s3", endpoint_url=self.endpoint, region_name="us-east-1",
            aws_access_key_id="testing", aws_secret_access_key="testing",
        ).put_object(Bucket=self.BUCKET, Key=key, Body=body, ContentType=ctype)

    def _make_s3(self):
        from services.storage_service import S3Storage
        return S3Storage(
            bucket=self.BUCKET, endpoint_url=self.endpoint, region="us-east-1",
            access_key="testing", secret_key="testing",
        )

    def test_instantiation_no_network(self):
        from services.storage_service import S3Storage
        s = S3Storage(bucket="x", endpoint_url="http://fake:9000",
                      region="us-east-1", access_key="a", secret_key="b")
        assert s.bucket == "x"
        assert s._endpoint == "http://fake:9000"

    def test_save_open_local_delete_cycle(self):
        """Save → open_local → delete. NOTE: stream() is tested separately;
        it has a known bug (client context closed before iterator consumed)."""
        s3 = self._make_s3()
        payload = b"mock-audio-bytes-" + b"z" * 4096
        key = "lectures/abc/audio.mp3"

        async def go():
            await s3.save(key, io.BytesIO(payload), "audio/mpeg")

            async with s3.open_local(key) as p:
                assert p.exists()
                assert p.read_bytes() == payload
            assert not p.exists()

            await s3.delete(key)
            await s3.delete(key)  # idempotent
        _arun(go())

    def test_stream_against_seeded_object(self):
        """Read path against an object seeded by sync boto3 (matches MinIO real-world)."""
        s3 = self._make_s3()
        payload = b"seeded-bytes"
        key = "lectures/xyz/audio.mp3"
        self._seed(key, payload, "audio/mpeg")

        async def go():
            it, size, ctype = await s3.stream(key)
            assert size == len(payload)
            assert ctype == "audio/mpeg"
            collected = b""
            async for chunk in it:
                collected += chunk
            assert collected == payload
        _arun(go())

class TestS3StorageFakes:
    def _make_s3(self, client_fake):
        from services.storage_service import S3Storage
        s = S3Storage("mybucket", None, "us-east-1", "a", "b")
        
        class MockSession:
            def client(self, *args, **kwargs):
                return client_fake
                
        s._session = MockSession()
        return s

    def test_head_object(self):
        class FakeClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def head_object(self, **kwargs):
                return {"ContentLength": 123, "ContentType": "image/png"}
                
        fake = FakeClient()
        s3 = self._make_s3(fake)
        
        async def go():
            res = await s3.head_object("foo.png")
            assert res == {"size": 123, "content_type": "image/png"}
        _arun(go())

    def test_head_object_not_found(self):
        from botocore.exceptions import ClientError
        class FakeClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def head_object(self, **kwargs):
                raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
                
        fake = FakeClient()
        s3 = self._make_s3(fake)
        
        async def go():
            with pytest.raises(FileNotFoundError):
                await s3.head_object("foo.png")
        _arun(go())

    def test_presign_post(self):
        class FakeClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def generate_presigned_post(self, **kwargs):
                self.kwargs = kwargs
                return {"url": "http://fake", "fields": {}}
                
        fake = FakeClient()
        s3 = self._make_s3(fake)
        
        async def go():
            res = await s3.presign_post("foo.mp4", "video/mp4", max_bytes=300*1024*1024, expires=1000)
            assert res == {"url": "http://fake", "fields": {}}
            assert fake.kwargs["Bucket"] == "mybucket"
            assert fake.kwargs["Key"] == "foo.mp4"
            assert fake.kwargs["ExpiresIn"] == 900
            assert fake.kwargs["Conditions"] == [
                ["content-length-range", 1, 200*1024*1024],
                {"Content-Type": "video/mp4"}
            ]
        _arun(go())

    def test_presign_get(self):
        class FakeClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def generate_presigned_url(self, op, Params, ExpiresIn):
                self.op = op
                self.Params = Params
                self.ExpiresIn = ExpiresIn
                return "http://fake-get"
                
        fake = FakeClient()
        s3 = self._make_s3(fake)
        
        async def go():
            url = await s3.presign_get("foo.mp4", expires=1000)
            assert url == "http://fake-get"
            assert fake.op == "get_object"
            assert fake.Params == {"Bucket": "mybucket", "Key": "foo.mp4"}
            assert fake.ExpiresIn == 900
        _arun(go())
