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
        retry_count = 0
        connection_count = 0

        state = DownloadState.FAILED

        while True:
            existing_size = 0

            if await self.storage.exists(request.destination):
                existing_data = await self.storage.read(
                    request.destination
                )
                existing_size = len(existing_data)

            headers: dict[str, str] | None = None

            if existing_size > 0:
                headers = {
                    "Range": f"bytes={existing_size}-",
                }

            try:
                response = await self.network.get(
                    request.url,
                    headers=headers,
                )
                connection_count += 1

                if existing_size > 0:
                    if response.status_code == 206:
                        append_mode = True
                        downloaded_bytes = existing_size

                    elif response.status_code == 200:
                        # Server ignored Range. Restart safely.
                        await self.storage.delete(
                            request.destination
                        )
                        append_mode = False
                        downloaded_bytes = 0

                    else:
                        raise RuntimeError(
                            f"Unable to resume download: "
                            f"HTTP {response.status_code}"
                        )
                else:
                    if response.status_code != 200:
                        raise RuntimeError(
                            f"Download failed: "
                            f"HTTP {response.status_code}"
                        )

                    append_mode = False
                    downloaded_bytes = 0

                hasher = sha256()

                if append_mode:
                    existing_data = await self.storage.read(
                        request.destination
                    )
                    hasher.update(existing_data)

                else:
                    await self.storage.write(
                        request.destination,
                        b"",
                    )

                async for chunk in response.body:
                    if not chunk:
                        continue

                    transferred_bytes += len(chunk)
                    downloaded_bytes += len(chunk)

                    hasher.update(chunk)

                    await self.storage.append(
                        request.destination,
                        chunk,
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

                break

            except Exception:
                state = DownloadState.FAILED

                if retry_count >= request.max_retries:
                    break

                retry_count += 1

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
            requested_bytes=(
                request.expected_size
                or downloaded_bytes
            ),
            transferred_bytes=transferred_bytes,
            retry_count=retry_count,
            connection_count=connection_count,
            duration_seconds=duration,
        )

        return DownloadResult(
            progress=progress,
            stats=stats,
            destination=request.destination,
        )
