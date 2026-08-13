from __future__ import annotations

from dataclasses import dataclass

from apps.api.core.capabilities import (
    RuntimePolicy,
    derive_policy,
)
from apps.api.platform.adapters import (
    HttpNetworkClient,
    LocalFileStorage,
    SubprocessRunner,
    SystemClock,
)
from apps.api.platform.contracts import (
    PlatformCapabilities,
    ResourceCapabilities,
    RuntimePaths,
)


@dataclass(frozen=True)
class Runtime:
    capabilities: PlatformCapabilities
    policy: RuntimePolicy


def create_runtime(
    *,
    capabilities: PlatformCapabilities | None = None,
) -> Runtime:
    if capabilities is None:
        capabilities = PlatformCapabilities(
            filesystem=LocalFileStorage(),
            network=HttpNetworkClient(),
            process=SubprocessRunner(),
            clock=SystemClock(),
            resources=ResourceCapabilities(
                execution_units=1,
                memory_total=1,
                memory_available=1,
                storage_total=1,
                storage_available=1,
            ),
            paths=RuntimePaths(
                config="config",
                data="data",
                cache="cache",
                logs="logs",
                runtime="runtime",
            ),
        )

    return Runtime(
        capabilities=capabilities,
        policy=derive_policy(
            capabilities.resources,
        ),
    )
