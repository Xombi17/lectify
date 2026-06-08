"""Simple load test: enqueue N jobs and verify they all get processed.

Usage:
  docker compose up -d redis
  python -m tests.load_test_queue --count=10
"""
import asyncio
import sys

from models.job import JobCreate
from services.queue_client import enqueue_job, get_queue_depth


async def load_test(count: int = 10):
    print(f"Enqueueing {count} jobs...")
    start = asyncio.get_event_loop().time()

    tasks = []
    for i in range(count):
        payload = JobCreate(lecture_id=f"load-test-{i}", stage="transcribe")
        tasks.append(enqueue_job(payload))

    results = await asyncio.gather(*tasks)
    elapsed = asyncio.get_event_loop().time() - start

    success = sum(1 for r in results if r.status in ("queued", "completed"))
    print(f"Enqueued {success}/{count} jobs in {elapsed:.2f}s ({count / elapsed:.0f} jobs/s)")

    depth = await get_queue_depth()
    print(f"Queue depth: {depth}")
    return success == count


if __name__ == "__main__":
    count = int(sys.argv[sys.argv.index("--count") + 1]) if "--count" in sys.argv else 10
    asyncio.run(load_test(count))
