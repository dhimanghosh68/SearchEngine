from __future__ import annotations

from typing import Protocol


class MetadataStore(Protocol):
    async def get(self, key: str) -> bytes | None:
        ...

    async def put(self, key: str, value: bytes) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def exists(self, key: str) -> bool:
        ...
