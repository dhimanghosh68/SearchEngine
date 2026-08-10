import pytest

from apps.api.download.contracts import (
    DownloadRequest,
    DownloadState,
)
from apps.api.download.manager import DownloadManager
from apps.api.platform.contracts import NetworkResponse


class FakeNetwork:
    def __init__(
        self,
        chunks: list[bytes],
        *,
        status_code: int = 200,
    ) -> None:
        self.chunks = chunks
        self.status_code = status_code
        self.last_headers: dict[str, str] | None = None

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ):
        self.last_headers = headers

        async def stream():
            for chunk in self.chunks:
                yield chunk

        return NetworkResponse(
            status_code=self.status_code,
            headers={
                "content-length": str(
                    sum(map(len, self.chunks))
                )
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
async def test_download_streams_data_into_storage():
    network = FakeNetwork(
        [
            b"hello ",
            b"world",
        ]
    )
    storage = FakeStorage()
    clock = FakeClock()

    manager = DownloadManager(
        network=network,
        storage=storage,
        clock=clock,
    )

    result = await manager.download(
        DownloadRequest(
            url="https://example.com/file.bin",
            destination="file.bin",
            expected_size=11,
        )
    )

    assert storage.files["file.bin"] == b"hello world"
    assert result.progress.state == DownloadState.COMPLETED
    assert result.progress.downloaded_bytes == 11
    assert result.stats.transferred_bytes == 11
    assert result.stats.connection_count == 1


@pytest.mark.asyncio
async def test_download_rejects_wrong_size():
    network = FakeNetwork([b"hello"])
    storage = FakeStorage()
    clock = FakeClock()

    manager = DownloadManager(
        network=network,
        storage=storage,
        clock=clock,
    )

    result = await manager.download(
        DownloadRequest(
            url="https://example.com/file.bin",
            destination="file.bin",
            expected_size=10,
        )
    )

    assert result.progress.state == DownloadState.FAILED


@pytest.mark.asyncio
async def test_download_verifies_sha256():
    network = FakeNetwork([b"hello"])
    storage = FakeStorage()
    clock = FakeClock()

    manager = DownloadManager(
        network=network,
        storage=storage,
        clock=clock,
    )

    result = await manager.download(
        DownloadRequest(
            url="https://example.com/file.bin",
            destination="file.bin",
            expected_size=5,
            expected_sha256=(
                "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
            ),
        )
    )

    assert result.progress.state == DownloadState.COMPLETED


@pytest.mark.asyncio
async def test_download_resumes_partial_file():
    network = FakeNetwork(
        [b"world"],
        status_code=206,
    )
    storage = FakeStorage()
    storage.files["file.bin"] = b"hello "

    clock = FakeClock()

    manager = DownloadManager(
        network=network,
        storage=storage,
        clock=clock,
    )

    result = await manager.download(
        DownloadRequest(
            url="https://example.com/file.bin",
            destination="file.bin",
            expected_size=11,
        )
    )

    assert result.progress.state == DownloadState.COMPLETED
    assert storage.files["file.bin"] == b"hello world"
    assert result.stats.transferred_bytes == 5
    assert network.last_headers == {
        "Range": "bytes=6-",
    }


@pytest.mark.asyncio
async def test_download_restarts_when_server_ignores_range():
    network = FakeNetwork([b"hello world"])
    storage = FakeStorage()
    storage.files["file.bin"] = b"hello "

    clock = FakeClock()

    manager = DownloadManager(
        network=network,
        storage=storage,
        clock=clock,
    )

    result = await manager.download(
        DownloadRequest(
            url="https://example.com/file.bin",
            destination="file.bin",
            expected_size=11,
        )
    )

    assert result.progress.state == DownloadState.COMPLETED
    assert storage.files["file.bin"] == b"hello world"
    assert result.stats.transferred_bytes == 11
    assert network.last_headers == {
        "Range": "bytes=6-",
    }


@pytest.mark.asyncio
async def test_download_resume_verifies_complete_sha256():
    network = FakeNetwork(
        [b"world"],
        status_code=206,
    )
    storage = FakeStorage()
    storage.files["file.bin"] = b"hello "

    clock = FakeClock()

    manager = DownloadManager(
        network=network,
        storage=storage,
        clock=clock,
    )

    result = await manager.download(
        DownloadRequest(
            url="https://example.com/file.bin",
            destination="file.bin",
            expected_size=11,
            expected_sha256=(
                "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
            ),
        )
    )

    assert result.progress.state == DownloadState.COMPLETED
    assert storage.files["file.bin"] == b"hello world"
