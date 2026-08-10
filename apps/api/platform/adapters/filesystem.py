from __future__ import annotations

import asyncio
from pathlib import Path


class LocalFileStorage:
    async def read(self, path: str) -> bytes:
        return await asyncio.to_thread(
            Path(path).read_bytes
        )

    async def write(
        self,
        path: str,
        data: bytes,
    ) -> None:
        target = Path(path)

        await asyncio.to_thread(
            target.parent.mkdir,
            parents=True,
            exist_ok=True,
        )

        await asyncio.to_thread(
            target.write_bytes,
            data,
        )

    async def append(
        self,
        path: str,
        data: bytes,
    ) -> None:
        target = Path(path)

        await asyncio.to_thread(
            target.parent.mkdir,
            parents=True,
            exist_ok=True,
        )

        def append_bytes() -> None:
            with target.open("ab") as file:
                file.write(data)

        await asyncio.to_thread(append_bytes)

    async def exists(self, path: str) -> bool:
        return await asyncio.to_thread(
            Path(path).exists
        )

    async def delete(self, path: str) -> None:
        target = Path(path)

        def delete_file() -> None:
            try:
                target.unlink()
            except FileNotFoundError:
                pass

        await asyncio.to_thread(delete_file)

    async def mkdir(self, path: str) -> None:
        await asyncio.to_thread(
            Path(path).mkdir,
            parents=True,
            exist_ok=True,
        )

    async def move(
        self,
        source: str,
        destination: str,
    ) -> None:
        source_path = Path(source)
        destination_path = Path(destination)

        await asyncio.to_thread(
            destination_path.parent.mkdir,
            parents=True,
            exist_ok=True,
        )

        await asyncio.to_thread(
            source_path.replace,
            destination_path,
        )
