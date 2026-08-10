from apps.api.platform.contracts import PlatformCapabilities


class FakeStorage:
    async def read(self, path: str) -> bytes:
        return b""

    async def write(self, path: str, data: bytes) -> None:
        pass

    async def exists(self, path: str) -> bool:
        return False

    async def delete(self, path: str) -> None:
        pass

    async def mkdir(self, path: str) -> None:
        pass


class FakeNetwork:
    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        return b""


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
