from __future__ import annotations

import json
from dataclasses import dataclass

from apps.api.platform.contracts import FileStorage, RuntimePaths


STATE_FILE = "runtime-state.json"


@dataclass(frozen=True)
class RuntimeState:
    clean_shutdown: bool
    generation: int


async def load_state(
    filesystem: FileStorage,
    paths: RuntimePaths,
) -> RuntimeState:
    path = f"{paths.runtime}/{STATE_FILE}"

    if not await filesystem.exists(path):
        return RuntimeState(
            clean_shutdown=True,
            generation=0,
        )

    try:
        raw = await filesystem.read(path)
        payload = json.loads(raw.decode("utf-8"))

        return RuntimeState(
            clean_shutdown=bool(
                payload.get("clean_shutdown", False)
            ),
            generation=int(payload.get("generation", 0)),
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return RuntimeState(
            clean_shutdown=False,
            generation=0,
        )


async def save_state(
    filesystem: FileStorage,
    paths: RuntimePaths,
    state: RuntimeState,
) -> None:
    await filesystem.mkdir(paths.runtime)

    path = f"{paths.runtime}/{STATE_FILE}"

    payload = {
        "clean_shutdown": state.clean_shutdown,
        "generation": state.generation,
    }

    await filesystem.write(
        path,
        json.dumps(
            payload,
            sort_keys=True,
        ).encode("utf-8"),
    )
