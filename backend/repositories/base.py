"""Base repository protocol — defines the data-access contract.

Every concrete repository implements this so callers are decoupled
from the database library.
"""
from typing import Optional, Protocol, TypeVar

T = TypeVar("T")


class Repository(Protocol[T]):
    async def get_by_id(self, item_id: str) -> Optional[T]: ...
