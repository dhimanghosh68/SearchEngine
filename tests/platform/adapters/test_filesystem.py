from __future__ import annotations

import pytest

from apps.api.platform.adapters.filesystem import LocalFileStorage


@pytest.mark.asyncio
async def test_filesystem_write_read_append_exists_delete(
    tmp_path,
):
    storage = LocalFileStorage()
    path = str(tmp_path / "nested" / "file.bin")

    assert await storage.exists(path) is False

    await storage.write(path, b"hello")
    assert await storage.exists(path) is True
    assert await storage.read(path) == b"hello"

    await storage.append(path, b" world")
    assert await storage.read(path) == b"hello world"

    await storage.delete(path)
    assert await storage.exists(path) is False


@pytest.mark.asyncio
async def test_filesystem_move(
    tmp_path,
):
    storage = LocalFileStorage()

    source = str(tmp_path / "source.bin")
    destination = str(tmp_path / "nested" / "destination.bin")

    await storage.write(source, b"payload")
    await storage.move(source, destination)

    assert await storage.exists(source) is False
    assert await storage.read(destination) == b"payload"
