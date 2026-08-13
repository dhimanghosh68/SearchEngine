from __future__ import annotations

from dataclasses import dataclass

from apps.api.config.application import (
    ApplicationConfig,
    create_application_config,
)
from apps.api.core.runtime import Runtime, create_runtime
from apps.api.platform.adapters import (
    HttpNetworkClient,
    LocalFileStorage,
    SubprocessRunner,
    SystemClock,
)
from apps.api.platform.adapters.resources import SystemResourceProvider
from apps.api.platform.contracts import (
    PlatformCapabilities,
    RuntimePaths,
)
from apps.api.storage.local import LocalMetadataStore


@dataclass(frozen=True)
class ApplicationRuntime:
    runtime: Runtime
    config: ApplicationConfig
    metadata: LocalMetadataStore


def create_application_runtime(
    *,
    elasticsearch_url: str,
    index_name: str,
    paths: RuntimePaths,
    environment: str = "local",
) -> ApplicationRuntime:
    filesystem = LocalFileStorage()

    resource_provider = SystemResourceProvider()
    resources = resource_provider.capabilities()

    capabilities = PlatformCapabilities(
        filesystem=filesystem,
        network=HttpNetworkClient(),
        process=SubprocessRunner(),
        clock=SystemClock(),
        resources=resources,
        paths=paths,
    )

    runtime = create_runtime(
        capabilities=capabilities,
    )

    config = create_application_config(
        elasticsearch_url=elasticsearch_url,
        index_name=index_name,
        paths=paths,
        environment=environment,
    )

    metadata = LocalMetadataStore(
        filesystem=filesystem,
        root=paths.data,
    )

    return ApplicationRuntime(
        runtime=runtime,
        config=config,
        metadata=metadata,
    )
