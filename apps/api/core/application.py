from __future__ import annotations

from dataclasses import dataclass

from apps.api.config.application import (
    ApplicationConfig,
    create_application_config,
)
from apps.api.core.runtime import Runtime, create_runtime
from apps.api.download.controller import DownloadController
from apps.api.download.manager import DownloadManager
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
from apps.api.services.search import SearchService
from apps.api.storage.local import LocalMetadataStore


@dataclass(frozen=True)
class ApplicationRuntime:
    runtime: Runtime
    config: ApplicationConfig
    metadata: LocalMetadataStore
    search: SearchService
    downloads: DownloadController


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

    network = HttpNetworkClient()
    clock = SystemClock()
    process = SubprocessRunner()

    capabilities = PlatformCapabilities(
        filesystem=filesystem,
        network=network,
        process=process,
        clock=clock,
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

    search = SearchService(
        elasticsearch_url=elasticsearch_url,
        index_name=index_name,
    )

    download_manager = DownloadManager(
        network=network,
        storage=filesystem,
        clock=clock,
    )

    downloads = DownloadController(
        manager=download_manager,
    )

    return ApplicationRuntime(
        runtime=runtime,
        config=config,
        metadata=metadata,
        search=search,
        downloads=downloads,
    )
