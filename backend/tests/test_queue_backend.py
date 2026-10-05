"""Contract tests for QueueBackend implementations."""
import asyncio
import time
import pytest
import uuid
import json

from core.queue_backend import MemoryQueueBackend, SqsQueueBackend, QueueMessage

pytestmark = pytest.mark.asyncio

class FakeSqsClient:
    def __init__(self):
        self.queues = {}
        
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    
    def _q(self, url):
        if url not in self.queues:
            self.queues[url] = []
        return self.queues[url]
        
    async def send_message(self, QueueUrl, MessageBody, DelaySeconds=0, **kwargs):
        msg_id = str(uuid.uuid4())
        self._q(QueueUrl).append({
            "MessageId": msg_id,
            "Body": MessageBody,
            "visible_at": time.monotonic() + DelaySeconds,
            "rc": 0
        })
        return {"MessageId": msg_id}
        
    async def receive_message(self, QueueUrl, MaxNumberOfMessages=1, WaitTimeSeconds=0, VisibilityTimeout=300, AttributeNames=None, **kwargs):
        now = time.monotonic()
        q = self._q(QueueUrl)
        found = []
        for msg in q:
            if msg["visible_at"] <= now:
                found.append(msg)
                if len(found) == MaxNumberOfMessages:
                    break
        if not found and WaitTimeSeconds > 0:
            await asyncio.sleep(min(WaitTimeSeconds, 0.05))
            now = time.monotonic()
            for msg in q:
                if msg["visible_at"] <= now and msg not in found:
                    found.append(msg)
                    if len(found) == MaxNumberOfMessages:
                        break
        
        results = []
        for msg in found:
            msg["rc"] += 1
            receipt = str(uuid.uuid4())
            msg["receipt"] = receipt
            msg["visible_at"] = now + VisibilityTimeout
            results.append({
                "MessageId": msg["MessageId"],
                "Body": msg["Body"],
                "ReceiptHandle": receipt,
                "Attributes": {"ApproximateReceiveCount": str(msg["rc"])}
            })
        return {"Messages": results}
        
    async def delete_message(self, QueueUrl, ReceiptHandle, **kwargs):
        q = self._q(QueueUrl)
        for i, m in enumerate(q):
            if m.get("receipt") == ReceiptHandle:
                q.pop(i)
                return
                
    async def change_message_visibility(self, QueueUrl, ReceiptHandle, VisibilityTimeout, **kwargs):
        q = self._q(QueueUrl)
        for m in q:
            if m.get("receipt") == ReceiptHandle:
                m["visible_at"] = time.monotonic() + VisibilityTimeout
                return
                
    async def get_queue_attributes(self, QueueUrl, AttributeNames=None, **kwargs):
        return {"Attributes": {"ApproximateNumberOfMessages": str(len(self._q(QueueUrl)))}}


@pytest.fixture
def memory_backend():
    return MemoryQueueBackend()

@pytest.fixture
def sqs_backend(monkeypatch):
    monkeypatch.setenv("QUEUE_URL_TRANSCRIBE", "url_transcribe")
    monkeypatch.setenv("QUEUE_URL_DLQ", "url_dlq")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    
    backend = SqsQueueBackend()
    
    # patch the client
    fake = FakeSqsClient()
    def fake_client():
        return fake
    backend._client = fake_client
    return backend

@pytest.fixture(params=["memory", "sqs"])
def backend(request):
    if request.param == "memory":
        return request.getfixturevalue("memory_backend")
    return request.getfixturevalue("sqs_backend")

async def test_send_and_receive(backend):
    msg_id = await backend.send("transcribe", {"hello": "world"})
    assert msg_id
    
    msgs = await backend.receive("transcribe", max_messages=1, wait_seconds=0)
    assert len(msgs) == 1
    assert msgs[0].body == {"hello": "world"}
    assert msgs[0].receive_count == 1
    
    # second receive should yield nothing (invisible)
    msgs2 = await backend.receive("transcribe", max_messages=1, wait_seconds=0)
    assert len(msgs2) == 0

async def test_change_visibility(backend):
    await backend.send("transcribe", {"hello": "world"})
    msgs = await backend.receive("transcribe", max_messages=1, wait_seconds=0)
    
    # immediately visible
    await backend.change_visibility("transcribe", msgs[0].receipt, 0)
    
    msgs2 = await backend.receive("transcribe", max_messages=1, wait_seconds=0)
    assert len(msgs2) == 1
    assert msgs2[0].receive_count == 2

async def test_delete(backend):
    await backend.send("transcribe", {"hello": "world"})
    msgs = await backend.receive("transcribe", max_messages=1, wait_seconds=0)
    
    await backend.delete("transcribe", msgs[0].receipt)
    
    # make it visible if it wasn't deleted
    await backend.change_visibility("transcribe", msgs[0].receipt, 0)
    
    msgs2 = await backend.receive("transcribe", max_messages=1, wait_seconds=0)
    assert len(msgs2) == 0

async def test_depth_and_dlq(backend):
    await backend.send("transcribe", {"foo": "bar"})
    await backend.send("dlq", {"foo": "dlq"})
    
    assert await backend.depth("transcribe") == 1
    assert await backend.dlq_depth() == 1
