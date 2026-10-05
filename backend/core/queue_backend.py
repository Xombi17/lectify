"""Queue backend abstraction (Memory/SQS)."""
import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Protocol

@dataclass
class QueueMessage:
    message_id: str
    queue: str
    body: dict
    receipt: str
    receive_count: int

class QueueBackend(Protocol):
    async def send(self, queue: str, body: dict, delay_seconds: int = 0) -> str:
        ...

    async def receive(
        self, queue: str, max_messages: int = 1, wait_seconds: int = 20, visibility_timeout: int = 300
    ) -> list[QueueMessage]:
        ...

    async def delete(self, queue: str, receipt: str) -> None:
        ...

    async def change_visibility(self, queue: str, receipt: str, seconds: int) -> None:
        ...

    async def depth(self, queue: str) -> int:
        ...

    async def dlq_depth(self) -> int:
        ...


class MemoryQueueBackend:
    def __init__(self, clock=time.monotonic, max_receives: int = 5):
        self._queues: dict[str, list[dict]] = {}
        self._dlq: list[dict] = []
        self._clock = clock
        self._max_receives = max_receives
        
    def _get_q(self, queue: str) -> list[dict]:
        if queue not in self._queues:
            self._queues[queue] = []
        return self._queues[queue]

    async def send(self, queue: str, body: dict, delay_seconds: int = 0) -> str:
        msg_id = str(uuid.uuid4())
        visible_at = self._clock() + delay_seconds
        
        self._get_q(queue).append({
            "message_id": msg_id,
            "body": body,
            "visible_at": visible_at,
            "receive_count": 0,
            "receipt": None
        })
        return msg_id

    async def receive(
        self, queue: str, max_messages: int = 1, wait_seconds: int = 20, visibility_timeout: int = 300
    ) -> list[QueueMessage]:
        start = self._clock()
        q = self._get_q(queue)
        
        while True:
            now = self._clock()
            found = []
            
            # Find visible messages
            for msg in q:
                if msg["visible_at"] <= now:
                    found.append(msg)
                    if len(found) == max_messages:
                        break
                        
            if found:
                results = []
                for msg in found:
                    msg["receive_count"] += 1
                    
                    if msg["receive_count"] > self._max_receives:
                        # Move to DLQ
                        q.remove(msg)
                        self._dlq.append(msg)
                        continue
                        
                    msg["receipt"] = str(uuid.uuid4())
                    msg["visible_at"] = now + visibility_timeout
                    
                    results.append(QueueMessage(
                        message_id=msg["message_id"],
                        queue=queue,
                        body=msg["body"],
                        receipt=msg["receipt"],
                        receive_count=msg["receive_count"]
                    ))
                
                if results:
                    return results
            
            # If nothing found and we still have time, wait
            elapsed = self._clock() - start
            if elapsed >= wait_seconds:
                break
                
            await asyncio.sleep(min(wait_seconds - elapsed, 0.05))
            
        return []

    async def delete(self, queue: str, receipt: str) -> None:
        q = self._get_q(queue)
        for i, msg in enumerate(q):
            if msg.get("receipt") == receipt:
                q.pop(i)
                return

    async def change_visibility(self, queue: str, receipt: str, seconds: int) -> None:
        q = self._get_q(queue)
        for msg in q:
            if msg.get("receipt") == receipt:
                msg["visible_at"] = self._clock() + seconds
                return

    async def depth(self, queue: str) -> int:
        return len(self._get_q(queue))

    async def dlq_depth(self) -> int:
        return len(self._dlq) + len(self._get_q("dlq"))


_instance: QueueBackend | None = None

def get_queue_backend() -> QueueBackend:
    global _instance
    if _instance is None:
        from core.config import get_settings
        settings = get_settings()
        if settings.QUEUE_BACKEND == "sqs":
            _instance = SqsQueueBackend()
        else:
            _instance = MemoryQueueBackend(max_receives=settings.QUEUE_MAX_RECEIVES)
    return _instance

def reset_queue_backend() -> None:
    global _instance
    _instance = None


class SqsQueueBackend:
    def __init__(self):
        from core.config import get_settings
        import aioboto3
        self.settings = get_settings()
        self.session = aioboto3.Session(region_name=self.settings.AWS_REGION)

    def _resolve(self, queue: str) -> str:
        from core.queue_config import queue_for_stage
        if queue == "dlq":
            return self.settings.QUEUE_URL_DLQ
        return queue_for_stage(queue)

    def _client(self):
        return self.session.client("sqs")

    async def send(self, queue: str, body: dict, delay_seconds: int = 0) -> str:
        import json
        url = self._resolve(queue)
        async with self._client() as sqs:
            res = await sqs.send_message(
                QueueUrl=url,
                MessageBody=json.dumps(body),
                DelaySeconds=delay_seconds
            )
            return res.get("MessageId", "")

    async def receive(
        self, queue: str, max_messages: int = 1, wait_seconds: int = 20, visibility_timeout: int = 300
    ) -> list[QueueMessage]:
        import json
        url = self._resolve(queue)
        wait_seconds = min(wait_seconds, 20)
        
        async with self._client() as sqs:
            res = await sqs.receive_message(
                QueueUrl=url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_seconds,
                VisibilityTimeout=visibility_timeout,
                AttributeNames=["ApproximateReceiveCount"]
            )
            
            messages = []
            for m in res.get("Messages", []):
                rc = int(m.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
                messages.append(QueueMessage(
                    message_id=m["MessageId"],
                    queue=queue,
                    body=json.loads(m["Body"]),
                    receipt=m["ReceiptHandle"],
                    receive_count=rc
                ))
            return messages

    async def delete(self, queue: str, receipt: str) -> None:
        url = self._resolve(queue)
        async with self._client() as sqs:
            await sqs.delete_message(QueueUrl=url, ReceiptHandle=receipt)

    async def change_visibility(self, queue: str, receipt: str, seconds: int) -> None:
        url = self._resolve(queue)
        async with self._client() as sqs:
            await sqs.change_message_visibility(
                QueueUrl=url,
                ReceiptHandle=receipt,
                VisibilityTimeout=seconds
            )

    async def depth(self, queue: str) -> int:
        url = self._resolve(queue)
        async with self._client() as sqs:
            res = await sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["ApproximateNumberOfMessages"])
            return int(res.get("Attributes", {}).get("ApproximateNumberOfMessages", "0"))

    async def dlq_depth(self) -> int:
        url = self.settings.QUEUE_URL_DLQ
        async with self._client() as sqs:
            res = await sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["ApproximateNumberOfMessages"])
            return int(res.get("Attributes", {}).get("ApproximateNumberOfMessages", "0"))
