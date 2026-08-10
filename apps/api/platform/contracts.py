from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


class FileStorage(Protocol):
    async def read(self, path: str) -> bytes:
        ...

    async def write(self, path: str, data: bytes) -> None:
        ...

    async def exists(self, path: str) -> bool:
        ...

    async def delete(self, path: str) -> None:
        ...

    async def mkdir(self, path: str) -> None:
        ...


class NetworkClient(Protocol):
    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        ...


class ProcessRunner(Protocol):
    async def run(
        self,
        executable: str,
        arguments: Sequence[str] = (),
    ) -> int:
        ...


class Clock(Protocol):
    def now(self) -> float:
        ...


@dataclass(frozen=True)
class PlatformCapabilities:
    filesystem: FileStorage
    network: NetworkClient
    process: ProcessRunner
    clock: Clock
