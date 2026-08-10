import asyncio

import pytest

from apps.api.download.contracts import (
    DownloadRequest,
    DownloadState,
)
from apps.api.download.controller import (
    DownloadController,
    DownloadOperation,
)
from apps.api.download.manager import DownloadManager
from apps.api.platform.contracts import NetworkResponse


class BlockingNetwork:
    def __init__(
        self,
        first_chunk: bytes = b"hello",
    ) -> None:
        self.first_chunk = first_chunk
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ):
        async def stream():
            yield self.first_chunk
            self.started.set()
            await self.release.wait()

        return NetworkResponse(
            status_code=200,
            headers={
                "content-length": "11",
            },
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


@pytest.mark.asyncio
async def test_controller_pauses_active_download():
    network = BlockingNetwork(
        first_chunk=b"hello ",
    )
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
        expected_size=11,
    )

    task = asyncio.create_task(controller.start(request))

    await network.started.wait()

    await controller.pause("file.bin")

    assert (
        controller.status("file.bin")
        == DownloadState.PAUSED
    )
    assert storage.files["file.bin"] == b"hello "

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_controller_resume_uses_persisted_file():
    class ResumeNetwork:
        def __init__(self) -> None:
            self.headers: list[dict[str, str] | None] = []

        async def get(
            self,
            url: str,
            *,
            headers: dict[str, str] | None = None,
        ):
            self.headers.append(headers)

            async def stream():
                yield b"world"

            return NetworkResponse(
                status_code=206,
                headers={
                    "content-range": "bytes 6-10/11",
                    "content-length": "5",
                },
                body=stream(),
            )

    network = ResumeNetwork()
    storage = FakeStorage()
    storage.files["file.bin"] = b"hello "

    manager = DownloadManager(
        network=network,
        storage=storage,
        clock=FakeClock(),
    )
    controller = DownloadController(manager=manager)

    request = DownloadRequest(
        url="https://example.com/file.bin",
        destination="file.bin",
        expected_size=11,
    )

    async def completed_task() -> None:
        return None

    operation_task = asyncio.create_task(
        completed_task()
    )
    await operation_task

    operation = DownloadOperation(
        request=request,
        task=operation_task,
        state=DownloadState.PAUSED,
    )

    controller._operations["file.bin"] = operation

    progress = await controller.resume("file.bin")

    assert progress.state == DownloadState.COMPLETED
    assert storage.files["file.bin"] == b"hello world"
    assert network.headers == [
        {"Range": "bytes=6-"}
    ]


@pytest.mark.asyncio
async def test_controller_cannot_cancel_completed_download():
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
    network.release.set()

    progress = await task

    assert progress.state == DownloadState.COMPLETED

    with pytest.raises(RuntimeError, match="completed"):
        await controller.cancel("file.bin")

    assert (
        controller.status("file.bin")
        == DownloadState.COMPLETED
    )


@pytest.mark.asyncio
async def test_controller_cannot_pause_cancelled_download():
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

    with pytest.raises(RuntimeError, match="cancelled"):
        await controller.pause("file.bin")


@pytest.mark.asyncio
async def test_controller_cannot_resume_cancelled_download():
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

    with pytest.raises(RuntimeError, match="cancelled"):
        await controller.resume("file.bin")


@pytest.mark.asyncio
async def test_controller_rejects_duplicate_active_download():
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

    with pytest.raises(
        RuntimeError,
        match="already active",
    ):
        await controller.start(request)

    await controller.cancel("file.bin")

    with pytest.raises(asyncio.CancelledError):
        await task
