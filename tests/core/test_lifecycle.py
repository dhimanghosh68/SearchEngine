import pytest

from apps.api.core.lifecycle import shutdown, startup
from apps.api.platform.contracts import RuntimePaths


class FakeStorage:
    def __init__(self):
        self.files = {}

    async def read(self, path):
        return self.files[path]

    async def write(self, path, data):
        self.files[path] = data

    async def append(self, path, data):
        self.files[path] = self.files.get(path, b"") + data

    async def exists(self, path):
        return path in self.files

    async def delete(self, path):
        self.files.pop(path, None)

    async def mkdir(self, path):
        pass

    async def move(self, source, destination):
        self.files[destination] = self.files.pop(source)


@pytest.fixture
def paths():
    return RuntimePaths(
        config="config",
        data="data",
        cache="cache",
        logs="logs",
        runtime="runtime",
    )


@pytest.mark.asyncio
async def test_first_start_does_not_require_recovery(
    paths,
):
    storage = FakeStorage()

    result = await startup(
        storage,
        paths,
    )

    assert result.recovery_required is False
    assert result.state.generation == 1
    assert result.state.clean_shutdown is False


@pytest.mark.asyncio
async def test_unclean_previous_run_requires_recovery(
    paths,
):
    storage = FakeStorage()

    first = await startup(
        storage,
        paths,
    )

    assert first.recovery_required is False

    second = await startup(
        storage,
        paths,
    )

    assert second.recovery_required is True
    assert second.state.generation == 2


@pytest.mark.asyncio
async def test_clean_shutdown_prevents_false_recovery(
    paths,
):
    storage = FakeStorage()

    first = await startup(
        storage,
        paths,
    )

    await shutdown(
        storage,
        paths,
        first.state,
    )

    second = await startup(
        storage,
        paths,
    )

    assert second.recovery_required is False
    assert second.state.generation == 2
