from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol, Sequence


@dataclass(frozen=True)
class NetworkResponse:
    status_code: int
    headers: dict[str, str]
    body: AsyncIterator[bytes]


class FileStorage(Protocol):
    async def read(self, path: str) -> bytes:
        ...

    async def write(self, path: str, data: bytes) -> None:
        ...

    async def append(self, path: str, data: bytes) -> None:
        ...

    async def exists(self, path: str) -> bool:
        ...

    async def delete(self, path: str) -> None:
        ...

    async def mkdir(self, path: str) -> None:
        ...

    async def move(self, source: str, destination: str) -> None:
        ...


class NetworkClient(Protocol):
    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> NetworkResponse:
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
class ResourceCapabilities:
    execution_units: int
    memory_total: int
    memory_available: int
    storage_total: int
    storage_available: int
    network_available: bool = True
    background_execution: bool = True


@dataclass(frozen=True)
class RuntimePaths:
    config: str
    data: str
    cache: str
    logs: str
    runtime: str


@dataclass(frozen=True)
class PlatformCapabilities:
    filesystem: FileStorage
    network: NetworkClient
    process: ProcessRunner
    clock: Clock
    resources: ResourceCapabilities = field(
        default_factory=lambda: ResourceCapabilities(
            execution_units=1,
            memory_total=1,
            memory_available=1,
            storage_total=1,
            storage_available=1,
        )
    )
    paths: RuntimePaths = field(
        default_factory=lambda: RuntimePaths(
            config="config",
            data="data",
            cache="cache",
            logs="logs",
            runtime="runtime",
        )
    )
