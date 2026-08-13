import pytest

from apps.api.storage.local import LocalMetadataStore


class FakeStorage:
    def __init__(self):
        self.files = {}
        self.directories = set()

    async def read(self, path):
        return self.files[path]

    async def write(self, path, data):
        self.files[path] = data

    async def append(self, path, data):
        self.files[path] = self.files.get(path, b"") + data

    async def exists(self, path):
        return path in self.files

    async def delete(self, path):
        self.files.pop(path, None)

    async def mkdir(self, path):
        self.directories.add(path)

    async def move(self, source, destination):
        self.files[destination] = self.files.pop(source)


@pytest.mark.asyncio
async def test_local_metadata_store_put_and_get():
    storage = FakeStorage()
    store = LocalMetadataStore(storage, "metadata")

    await store.put("example", b"value")

    assert await store.exists("example")
    assert await store.get("example") == b"value"
    assert "metadata" in storage.directories


@pytest.mark.asyncio
async def test_local_metadata_store_delete():
    storage = FakeStorage()
    store = LocalMetadataStore(storage, "metadata")

    await store.put("example", b"value")
    await store.delete("example")

    assert not await store.exists("example")
    assert await store.get("example") is None


@pytest.mark.asyncio
async def test_local_metadata_store_rejects_traversal():
    storage = FakeStorage()
    store = LocalMetadataStore(storage, "metadata")

    with pytest.raises(ValueError):
        await store.put("../outside", b"value")


@pytest.mark.asyncio
async def test_local_metadata_store_rejects_empty_key():
    storage = FakeStorage()
    store = LocalMetadataStore(storage, "metadata")

    with pytest.raises(ValueError):
        await store.put("", b"value")
