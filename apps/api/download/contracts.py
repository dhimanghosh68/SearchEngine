from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DownloadState(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class DownloadRequest:
    url: str
    destination: str
    expected_size: int | None = None
    expected_sha256: str | None = None
    max_retries: int = 3
    chunk_size: int = 1024 * 1024
    max_concurrency: int = 4


@dataclass(frozen=True)
class DownloadProgress:
    downloaded_bytes: int
    total_bytes: int | None
    state: DownloadState

    @property
    def completed(self) -> bool:
        return self.state == DownloadState.COMPLETED

    @property
    def percentage(self) -> float | None:
        if self.total_bytes is None or self.total_bytes <= 0:
            return None

        return (
            self.downloaded_bytes
            / self.total_bytes
            * 100
        )
