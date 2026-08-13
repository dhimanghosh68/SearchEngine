from __future__ import annotations

from apps.api.platform.contracts import FileStorage
from apps.api.storage.contracts import MetadataStore


class LocalMetadataStore(MetadataStore):
    def __init__(
        self,
        filesystem: FileStorage,
        root: str,
    ) -> None:
        self.filesystem = filesystem
        self.root = root

    def _path(self, key: str) -> str:
        normalized = key.strip("/")

        if not normalized:
            raise ValueError("Metadata key cannot be empty")

        if ".." in normalized.split("/"):
            raise ValueError("Invalid metadata key")

        return f"{self.root}/{normalized}"

    async def get(self, key: str) -> bytes | None:
        path = self._path(key)

        if not await self.filesystem.exists(path):
            return None

        return await self.filesystem.read(path)

    async def put(self, key: str, value: bytes) -> None:
        path = self._path(key)

        parent = path.rsplit("/", 1)[0]
        await self.filesystem.mkdir(parent)

        temporary = f"{path}.tmp"
        await self.filesystem.write(temporary, value)
        await self.filesystem.move(temporary, path)

    async def delete(self, key: str) -> None:
        path = self._path(key)

        if await self.filesystem.exists(path):
            await self.filesystem.delete(path)

    async def exists(self, key: str) -> bool:
        return await self.filesystem.exists(self._path(key))
