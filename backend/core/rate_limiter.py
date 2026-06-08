"""Simple in-memory rate limiter. Not distributed — replace with Redis in Phase 5."""
import time
from collections import defaultdict


class InMemoryRateLimiter:
    """Per-process in-memory rate limiter using a sliding-window approach.

    NOTE: This is a per-process limiter. Replace with a Redis-based distributed
    limiter in Phase 5 (queue + worker system) when running multiple workers.
    """

    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def check(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        """Check if a request is allowed for the given key.

        Returns True if the request is within the rate limit, False otherwise.
        """
        now = time.time()
        bucket = self._buckets[key]

        # Clean expired entries older than the window
        while bucket and bucket[0] < now - window_seconds:
            bucket.pop(0)

        if len(bucket) >= max_requests:
            return False

        bucket.append(now)
        return True

    async def remaining(self, key: str, max_requests: int, window_seconds: int = 60) -> int:
        """Get the number of remaining requests allowed for the given key."""
        now = time.time()
        bucket = self._buckets[key]

        # Clean expired entries
        while bucket and bucket[0] < now - window_seconds:
            bucket.pop(0)

        return max(0, max_requests - len(bucket))

    async def reset(self, key: str) -> None:
        """Reset the rate limit counter for a given key."""
        self._buckets[key] = []
