from apps.api.core.runtime import create_runtime
from apps.api.platform.contracts import (
    PlatformCapabilities,
    ResourceCapabilities,
    RuntimePaths,
)


def test_runtime_capabilities_are_fully_constructed():
    runtime = create_runtime()

    capabilities = runtime.capabilities

    assert capabilities.filesystem is not None
    assert capabilities.network is not None
    assert capabilities.process is not None
    assert capabilities.clock is not None
    assert capabilities.resources is not None
    assert capabilities.paths is not None


def test_runtime_accepts_arbitrary_capabilities():
    capabilities = PlatformCapabilities(
        filesystem=object(),
        network=object(),
        process=object(),
        clock=object(),
        resources=ResourceCapabilities(
            execution_units=2,
            memory_total=4 * 1024 * 1024 * 1024,
            memory_available=2 * 1024 * 1024 * 1024,
            storage_total=4096,
            storage_available=2048,
        ),
        paths=RuntimePaths(
            config="a",
            data="b",
            cache="c",
            logs="d",
            runtime="e",
        ),
    )

    runtime = create_runtime(
        capabilities=capabilities,
    )

    assert runtime.capabilities is capabilities
    assert runtime.policy.workers == 2


def test_runtime_uses_resource_provider():
    class FakeResourceProvider:
        def capabilities(self):
            return ResourceCapabilities(
                execution_units=4,
                memory_total=4 * 1024 * 1024 * 1024,
                memory_available=2 * 1024 * 1024 * 1024,
                storage_total=100,
                storage_available=50,
            )

    runtime = create_runtime(
        resource_provider=FakeResourceProvider(),
    )

    assert runtime.capabilities.resources.execution_units == 4
    assert runtime.capabilities.resources.memory_available == (
        2 * 1024 * 1024 * 1024
    )
    assert runtime.policy.workers == 4
    assert runtime.policy.download_concurrency == 4
