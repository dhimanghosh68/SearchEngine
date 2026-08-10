from __future__ import annotations

from dataclasses import dataclass

from apps.api.platform.adapters import (
    HttpNetworkClient,
    LocalFileStorage,
    SubprocessRunner,
    SystemClock,
)
from apps.api.platform.contracts import PlatformCapabilities


@dataclass(frozen=True)
class Runtime:
    capabilities: PlatformCapabilities


def create_runtime() -> Runtime:
    capabilities = PlatformCapabilities(
        filesystem=LocalFileStorage(),
        network=HttpNetworkClient(),
        process=SubprocessRunner(),
        clock=SystemClock(),
    )

    return Runtime(
        capabilities=capabilities,
    )
def test_runtime_capabilities_are_fully_constructed():
    runtime = create_runtime()
    capabilities = runtime.capabilities

    assert capabilities.filesystem is not None
    assert capabilities.network is not None
    assert capabilities.process is not None
    assert capabilities.clock is not None