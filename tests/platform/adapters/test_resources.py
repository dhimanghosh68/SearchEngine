from apps.api.platform.adapters.resources import SystemResourceProvider


class FakeUsage:
    total = 1000
    free = 400


def test_resource_provider_returns_capabilities(monkeypatch):
    monkeypatch.setattr(
        "apps.api.platform.adapters.resources.os.cpu_count",
        lambda: 4,
    )

    monkeypatch.setattr(
        "apps.api.platform.adapters.resources.shutil.disk_usage",
        lambda path: FakeUsage(),
    )

    provider = SystemResourceProvider(
        storage_path=".",
    )

    capabilities = provider.capabilities()

    assert capabilities.execution_units == 4
    assert capabilities.storage_total == 1000
    assert capabilities.storage_available == 400
    assert capabilities.network_available is True
    assert capabilities.background_execution is True


def test_resource_provider_never_returns_negative_storage(monkeypatch):
    class NegativeUsage:
        total = -100
        free = -50

    monkeypatch.setattr(
        "apps.api.platform.adapters.resources.shutil.disk_usage",
        lambda path: NegativeUsage(),
    )

    provider = SystemResourceProvider()

    capabilities = provider.capabilities()

    assert capabilities.storage_total == 0
    assert capabilities.storage_available == 0
