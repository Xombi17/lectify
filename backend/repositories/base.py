"""Base repository protocol — defines the data-access contract.

Every concrete repository implements this so we can swap MongoDB → PostgreSQL
(or anything else) by only changing the implementation, not callers.
"""
from typing import Optional, Protocol, TypeVar

T = TypeVar("T")


class Repository(Protocol[T]):
    async def get_by_id(self, item_id: str) -> Optional[T]: ...
