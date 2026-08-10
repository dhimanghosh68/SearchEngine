from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from apps.api.download.contracts import (
    DownloadProgress,
    DownloadRequest,
    DownloadState,
    TransferStats,
)
from apps.api.platform.contracts import (
    Clock,
    FileStorage,
    NetworkClient,
)


@dataclass
class DownloadResult:
    progress: DownloadProgress
    stats: TransferStats
    destination: str


class DownloadManager:
    def __init__(
        self,
        *,
        network: NetworkClient,
        storage: FileStorage,
        clock: Clock,
    ) -> None:
        self.network = network
        self.storage = storage
        self.clock = clock

    async def download(
        self,
        request: DownloadRequest,
    ) -> DownloadResult:
        started_at = self.clock.now()

        downloaded_bytes = 0
        transferred_bytes = 0

        hasher = sha256()

        try:
            stream = await self.network.get(request.url)

            async for chunk in stream:
                if not chunk:
                    continue

                downloaded_bytes += len(chunk)
                transferred_bytes += len(chunk)

                hasher.update(chunk)

                await self.storage.append(
                    request.destination,
                    chunk,
                )

        except Exception:
            duration = max(
                0.0,
                self.clock.now() - started_at,
            )

            progress = DownloadProgress(
                downloaded_bytes=downloaded_bytes,
                total_bytes=request.expected_size,
                state=DownloadState.FAILED,
            )

            stats = TransferStats(
                requested_bytes=request.expected_size or downloaded_bytes,
                transferred_bytes=transferred_bytes,
                retry_count=0,
                connection_count=1,
                duration_seconds=duration,
            )

            return DownloadResult(
                progress=progress,
                stats=stats,
                destination=request.destination,
            )

        if (
            request.expected_size is not None
            and downloaded_bytes != request.expected_size
        ):
            state = DownloadState.FAILED
        elif (
            request.expected_sha256 is not None
            and hasher.hexdigest().lower()
            != request.expected_sha256.lower()
        ):
            state = DownloadState.FAILED
        else:
            state = DownloadState.COMPLETED

        duration = max(
            0.0,
            self.clock.now() - started_at,
        )

        progress = DownloadProgress(
            downloaded_bytes=downloaded_bytes,
            total_bytes=request.expected_size,
            state=state,
        )

        stats = TransferStats(
            requested_bytes=request.expected_size or downloaded_bytes,
            transferred_bytes=transferred_bytes,
            retry_count=0,
            connection_count=1,
            duration_seconds=duration,
        )

        return DownloadResult(
            progress=progress,
            stats=stats,
            destination=request.destination,
        )
