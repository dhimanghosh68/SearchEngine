import sys

import pytest

from apps.api.platform.adapters.process import SubprocessRunner


@pytest.mark.asyncio
async def test_process_runner_returns_exit_code():
    runner = SubprocessRunner()

    code = await runner.run(
        sys.executable,
        [
            "-c",
            "raise SystemExit(0)",
        ],
    )

    assert code == 0


@pytest.mark.asyncio
async def test_process_runner_returns_failure_exit_code():
    runner = SubprocessRunner()

    code = await runner.run(
        sys.executable,
        [
            "-c",
            "raise SystemExit(7)",
        ],
    )

    assert code == 7
