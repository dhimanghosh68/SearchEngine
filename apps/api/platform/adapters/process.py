from __future__ import annotations

import asyncio
from typing import Sequence


class SubprocessRunner:
    async def run(
        self,
        executable: str,
        arguments: Sequence[str] = (),
    ) -> int:
        process = await asyncio.create_subprocess_exec(
            executable,
            *arguments,
        )

        return await process.wait()
