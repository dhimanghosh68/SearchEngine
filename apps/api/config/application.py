from __future__ import annotations

from dataclasses import dataclass

from apps.api.platform.contracts import RuntimePaths


@dataclass(frozen=True)
class ApplicationConfig:
    service_name: str
    environment: str
    elasticsearch_url: str
    index_name: str
    paths: RuntimePaths


def create_application_config(
    *,
    elasticsearch_url: str,
    index_name: str,
    paths: RuntimePaths,
    environment: str = "local",
) -> ApplicationConfig:
    return ApplicationConfig(
        service_name="search-engine",
        environment=environment,
        elasticsearch_url=elasticsearch_url,
        index_name=index_name,
        paths=paths,
    )
