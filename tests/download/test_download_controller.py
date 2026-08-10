import asyncio

import pytest

from apps.api.download.contracts import (
    DownloadRequest,
    DownloadState,
)
from apps.api.download.controller import DownloadController
from apps.api.download.manager import DownloadManager
from apps.api.platform.contracts import NetworkResponse


class BlockingNetwork:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ):
        async def stream():
            self.started.set()
            await self.release.wait()
            yield b"hello"

        return NetworkResponse(
            status_code=200,
            headers={"content-length": "5"},
            body=stream(),
        )


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def read(self, path: str) -> bytes:
        return self.files.get(path, b"")

    async def write(self, path: str, data: bytes) -> None:
        self.files[path] = data

    async def append(self, path: str, data: bytes) -> None:
        self.files[path] = self.files.get(path, b"") + data

    async def exists(self, path: str) -> bool:
        return path in self.files

    async def delete(self, path: str) -> None:
        self.files.pop(path, None)

    async def mkdir(self, path: str) -> None:
        pass

    async def move(self, source: str, destination: str) -> None:
        self.files[destination] = self.files.pop(source)


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def now(self) -> float:
        self.value += 1.0
        return self.value


@pytest.mark.asyncio
async def test_controller_starts_download():
    network = BlockingNetwork()
    storage = FakeStorage()
    manager = DownloadManager(
        network=network,
        storage=storage,
        clock=FakeClock(),
    )
    controller = DownloadController(manager=manager)

    request = DownloadRequest(
        url="https://example.com/file.bin",
        destination="file.bin",
        expected_size=5,
    )

    task = asyncio.create_task(controller.start(request))

    await network.started.wait()

    assert (
        controller.status("file.bin")
        == DownloadState.DOWNLOADING
    )

    network.release.set()

    progress = await task

    assert progress.state == DownloadState.COMPLETED
    assert (
        controller.status("file.bin")
        == DownloadState.COMPLETED
    )


@pytest.mark.asyncio
async def test_controller_cancels_active_download():
    network = BlockingNetwork()
    storage = FakeStorage()
    manager = DownloadManager(
        network=network,
        storage=storage,
        clock=FakeClock(),
    )
    controller = DownloadController(manager=manager)

    request = DownloadRequest(
        url="https://example.com/file.bin",
        destination="file.bin",
        expected_size=5,
    )

    task = asyncio.create_task(controller.start(request))

    await network.started.wait()

    await controller.cancel("file.bin")

    with pytest.raises(asyncio.CancelledError):
        await task

    assert (
        controller.status("file.bin")
        == DownloadState.CANCELLED
    )
