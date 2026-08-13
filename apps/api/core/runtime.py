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
    SystemResourceProvider,
)
from apps.api.platform.contracts import (
    PlatformCapabilities,
    ResourceProvider,
    RuntimePaths,
)


@dataclass(frozen=True)
class Runtime:
    capabilities: PlatformCapabilities
    policy: RuntimePolicy


def create_runtime(
    *,
    capabilities: PlatformCapabilities | None = None,
    resource_provider: ResourceProvider | None = None,
    paths: RuntimePaths | None = None,
) -> Runtime:
    if capabilities is None:
        if resource_provider is None:
            resource_provider = SystemResourceProvider(
                storage_path="."
            )

        resolved_paths = paths or RuntimePaths(
            config="config",
            data="data",
            cache="cache",
            logs="logs",
            runtime="runtime",
        )

        capabilities = PlatformCapabilities(
            filesystem=LocalFileStorage(),
            network=HttpNetworkClient(),
            process=SubprocessRunner(),
            clock=SystemClock(),
            resources=resource_provider.capabilities(),
            paths=resolved_paths,
        )

    return Runtime(
        capabilities=capabilities,
        policy=derive_policy(
            capabilities.resources,
        ),
    )
