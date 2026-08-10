from apps.api.platform.adapters.clock import SystemClock


def test_system_clock_is_monotonic():
    clock = SystemClock()

    first = clock.now()
    second = clock.now()

    assert second >= first
