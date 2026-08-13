from __future__ import annotations

from dataclasses import dataclass

from apps.api.core.state import (
    RuntimeState,
    load_state,
    save_state,
)
from apps.api.platform.contracts import (
    FileStorage,
    RuntimePaths,
)


@dataclass(frozen=True)
class StartupResult:
    state: RuntimeState
    recovery_required: bool


async def startup(
    filesystem: FileStorage,
    paths: RuntimePaths,
) -> StartupResult:
    previous = await load_state(
        filesystem,
        paths,
    )

    current = RuntimeState(
        clean_shutdown=False,
        generation=previous.generation + 1,
    )

    await save_state(
        filesystem,
        paths,
        current,
    )

    return StartupResult(
        state=current,
        recovery_required=not previous.clean_shutdown,
    )


async def shutdown(
    filesystem: FileStorage,
    paths: RuntimePaths,
    state: RuntimeState,
) -> None:
    await save_state(
        filesystem,
        paths,
        RuntimeState(
            clean_shutdown=True,
            generation=state.generation,
        ),
    )
