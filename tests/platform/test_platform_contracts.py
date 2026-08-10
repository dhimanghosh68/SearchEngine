import pytest

from apps.api.platform.contracts import PlatformCapabilities


class FakeStorage:
    async def read(self, path: str) -> bytes:
        return b""

    async def write(self, path: str, data: bytes) -> None:
        pass

    async def append(self, path: str, data: bytes) -> None:
        pass

    async def exists(self, path: str) -> bool:
        return False

    async def delete(self, path: str) -> None:
        pass

    async def mkdir(self, path: str) -> None:
        pass

    async def move(self, source: str, destination: str) -> None:
        pass


class FakeNetwork:
    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ):
        yield b"chunk-1"
        yield b"chunk-2"


class FakeProcess:
    async def run(
        self,
        executable: str,
        arguments: tuple[str, ...] = (),
    ) -> int:
        return 0


class FakeClock:
    def now(self) -> float:
        return 0.0


def test_platform_capabilities_accept_generic_implementations():
    capabilities = PlatformCapabilities(
        filesystem=FakeStorage(),
        network=FakeNetwork(),
        process=FakeProcess(),
        clock=FakeClock(),
    )

    assert capabilities.filesystem is not None
    assert capabilities.network is not None
    assert capabilities.process is not None
    assert capabilities.clock.now() == 0.0


@pytest.mark.asyncio
async def test_network_contract_supports_streaming():
    network = FakeNetwork()

    chunks = [
        chunk
        async for chunk in network.get(
            "https://example.com/file.bin"
        )
    ]

    assert chunks == [b"chunk-1", b"chunk-2"]
