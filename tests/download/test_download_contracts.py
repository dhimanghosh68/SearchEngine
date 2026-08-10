from apps.api.download.contracts import (
    DownloadProgress,
    DownloadRequest,
    DownloadState,
    TransferStats,
)


def test_download_request_has_safe_defaults():
    request = DownloadRequest(
        url="https://example.com/file.bin",
        destination="file.bin",
    )

    assert request.max_retries == 3
    assert request.chunk_size == 1024 * 1024
    assert request.max_concurrency == 4


def test_download_progress_percentage():
    progress = DownloadProgress(
        downloaded_bytes=50,
        total_bytes=100,
        state=DownloadState.DOWNLOADING,
    )

    assert progress.percentage == 50.0
    assert not progress.completed


def test_completed_download():
    progress = DownloadProgress(
        downloaded_bytes=100,
        total_bytes=100,
        state=DownloadState.COMPLETED,
    )

    assert progress.completed
    assert progress.percentage == 100.0


def test_unknown_total_size():
    progress = DownloadProgress(
        downloaded_bytes=100,
        total_bytes=None,
        state=DownloadState.DOWNLOADING,
    )

    assert progress.percentage is None


def test_transfer_stats_calculates_overhead():
    stats = TransferStats(
        requested_bytes=1_000,
        transferred_bytes=1_100,
        retry_count=1,
        connection_count=2,
        duration_seconds=2.0,
    )

    assert stats.overhead_bytes == 100


def test_transfer_stats_calculates_average_speed():
    stats = TransferStats(
        requested_bytes=1_000,
        transferred_bytes=2_000,
        retry_count=0,
        connection_count=1,
        duration_seconds=2.0,
    )

    assert stats.average_bytes_per_second == 1_000.0
