from __future__ import annotations

from dataclasses import dataclass

from apps.api.platform.contracts import ResourceCapabilities


@dataclass(frozen=True)
class RuntimePolicy:
    workers: int
    download_concurrency: int
    crawl_concurrency: int
    index_batch_size: int
    cache_budget: int


def derive_policy(resources: ResourceCapabilities) -> RuntimePolicy:
    units = max(resources.execution_units, 1)
    memory = max(resources.memory_available, 1)

    workers = max(1, min(units, 8))

    if memory < 512 * 1024 * 1024:
        workers = 1
        download_concurrency = 1
        crawl_concurrency = 1
        index_batch_size = 25
        cache_budget = min(memory // 8, 32 * 1024 * 1024)
    elif memory < 2 * 1024 * 1024 * 1024:
        download_concurrency = min(2, workers)
        crawl_concurrency = min(2, workers)
        index_batch_size = 100
        cache_budget = min(memory // 8, 128 * 1024 * 1024)
    else:
        download_concurrency = min(4, workers)
        crawl_concurrency = min(4, workers)
        index_batch_size = 250
        cache_budget = min(memory // 4, 512 * 1024 * 1024)

    if not resources.background_execution:
        download_concurrency = 1
        crawl_concurrency = 1

    if not resources.network_available:
        download_concurrency = 0
        crawl_concurrency = 0

    return RuntimePolicy(
        workers=workers,
        download_concurrency=download_concurrency,
        crawl_concurrency=crawl_concurrency,
        index_batch_size=index_batch_size,
        cache_budget=max(cache_budget, 1),
    )
