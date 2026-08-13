from apps.api.core.capabilities import derive_policy
from apps.api.platform.contracts import ResourceCapabilities


def test_policy_for_constrained_device():
    policy = derive_policy(
        ResourceCapabilities(
            execution_units=2,
            memory_total=512 * 1024 * 1024,
            memory_available=256 * 1024 * 1024,
            storage_total=10 * 1024 * 1024 * 1024,
            storage_available=5 * 1024 * 1024 * 1024,
        )
    )

    assert policy.workers == 1
    assert policy.download_concurrency == 1
    assert policy.crawl_concurrency == 1


def test_policy_for_larger_device():
    policy = derive_policy(
        ResourceCapabilities(
            execution_units=8,
            memory_total=16 * 1024 * 1024 * 1024,
            memory_available=8 * 1024 * 1024 * 1024,
            storage_total=500 * 1024 * 1024 * 1024,
            storage_available=250 * 1024 * 1024 * 1024,
        )
    )

    assert policy.workers == 8
    assert policy.download_concurrency == 4
    assert policy.crawl_concurrency == 4
    assert policy.index_batch_size == 250


def test_policy_disables_network_work_without_network():
    policy = derive_policy(
        ResourceCapabilities(
            execution_units=4,
            memory_total=4 * 1024 * 1024 * 1024,
            memory_available=2 * 1024 * 1024 * 1024,
            storage_total=100,
            storage_available=50,
            network_available=False,
        )
    )

    assert policy.download_concurrency == 0
    assert policy.crawl_concurrency == 0


def test_policy_limits_background_work():
    policy = derive_policy(
        ResourceCapabilities(
            execution_units=8,
            memory_total=8 * 1024 * 1024 * 1024,
            memory_available=4 * 1024 * 1024 * 1024,
            storage_total=100,
            storage_available=50,
            background_execution=False,
        )
    )

    assert policy.download_concurrency == 1
    assert policy.crawl_concurrency == 1
