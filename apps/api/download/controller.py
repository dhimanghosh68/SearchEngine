from __future__ import annotations

import asyncio
from dataclasses import dataclass

from apps.api.download.contracts import (
    DownloadProgress,
    DownloadRequest,
    DownloadState,
)
from apps.api.download.manager import DownloadManager


@dataclass
class DownloadOperation:
    request: DownloadRequest
    task: asyncio.Task
    state: DownloadState = DownloadState.PENDING
    result: object | None = None


class DownloadController:
    def __init__(
        self,
        *,
        manager: DownloadManager,
    ) -> None:
        self.manager = manager
        self._operations: dict[str, DownloadOperation] = {}

    async def start(
        self,
        request: DownloadRequest,
    ) -> DownloadProgress:
        existing = self._operations.get(request.destination)

        if existing is not None and not existing.task.done():
            raise RuntimeError(
                "Download is already active"
            )

        operation: DownloadOperation | None = None

        async def run() -> DownloadProgress:
            assert operation is not None

            operation.state = DownloadState.DOWNLOADING

            try:
                result = await self.manager.download(request)
                operation.result = result
                operation.state = result.progress.state
                return result.progress

            except asyncio.CancelledError:
                if operation.state != DownloadState.PAUSED:
                    operation.state = DownloadState.CANCELLED
                raise

            except Exception:
                operation.state = DownloadState.FAILED
                raise

        task = asyncio.create_task(run())

        operation = DownloadOperation(
            request=request,
            task=task,
            state=DownloadState.PENDING,
        )

        self._operations[request.destination] = operation

        return await task

    async def pause(self, destination: str) -> None:
        operation = self._require(destination)

        if operation.state == DownloadState.COMPLETED:
            raise RuntimeError(
                "Cannot pause a completed download"
            )

        if operation.state == DownloadState.FAILED:
            raise RuntimeError(
                "Cannot pause a failed download"
            )

        if operation.state == DownloadState.CANCELLED:
            raise RuntimeError(
                "Cannot pause a cancelled download"
            )

        if operation.task.done():
            return

        operation.state = DownloadState.PAUSED
        operation.task.cancel()

        try:
            await operation.task
        except asyncio.CancelledError:
            pass

        operation.state = DownloadState.PAUSED

    async def resume(
        self,
        destination: str,
    ) -> DownloadProgress:
        operation = self._require(destination)

        if not operation.task.done():
            raise RuntimeError(
                "Download is already active"
            )

        if operation.state != DownloadState.PAUSED:
            raise RuntimeError(
                f"Cannot resume download in state "
                f"{operation.state.value}"
            )

        return await self.start(operation.request)

    async def cancel(self, destination: str) -> None:
        operation = self._require(destination)

        if operation.state == DownloadState.COMPLETED:
            raise RuntimeError(
                "Cannot cancel a completed download"
            )

        if operation.state == DownloadState.FAILED:
            raise RuntimeError(
                "Cannot cancel a failed download"
            )

        if operation.state == DownloadState.CANCELLED:
            return

        operation.task.cancel()

        try:
            await operation.task
        except asyncio.CancelledError:
            pass

        operation.state = DownloadState.CANCELLED

    def status(self, destination: str) -> DownloadState:
        return self._require(destination).state

    def _require(self, destination: str) -> DownloadOperation:
        try:
            return self._operations[destination]
        except KeyError as exc:
            raise KeyError(
                f"No download operation for {destination!r}"
            ) from exc
