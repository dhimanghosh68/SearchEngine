from apps.api.core.runtime import Runtime, create_runtime
from apps.api.platform.adapters import (
    HttpNetworkClient,
    LocalFileStorage,
    SubprocessRunner,
    SystemClock,
)


def test_create_runtime_builds_platform_capabilities():
    runtime = create_runtime()

    assert isinstance(runtime, Runtime)

    assert isinstance(
        runtime.capabilities.filesystem,
        LocalFileStorage,
    )

    assert isinstance(
        runtime.capabilities.network,
        HttpNetworkClient,
    )

    assert isinstance(
        runtime.capabilities.process,
        SubprocessRunner,
    )

    assert isinstance(
        runtime.capabilities.clock,
        SystemClock,
    )

