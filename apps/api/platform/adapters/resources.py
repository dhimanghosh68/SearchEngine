from __future__ import annotations

import os
import shutil

from apps.api.platform.contracts import ResourceCapabilities


class SystemResourceProvider:
    def __init__(
        self,
        *,
        storage_path: str = ".",
        network_available: bool = True,
        background_execution: bool = True,
    ) -> None:
        self.storage_path = storage_path
        self._network_available = network_available
        self._background_execution = background_execution

    def capabilities(self) -> ResourceCapabilities:
        execution_units = max(os.cpu_count() or 1, 1)

        memory_total, memory_available = self._memory()

        storage_total, storage_available = self._storage()

        return ResourceCapabilities(
            execution_units=execution_units,
            memory_total=memory_total,
            memory_available=memory_available,
            storage_total=storage_total,
            storage_available=storage_available,
            network_available=self._network_available,
            background_execution=self._background_execution,
        )

    @staticmethod
    def _memory() -> tuple[int, int]:
        try:
            import psutil
        except ImportError:
            return 0, 0

        memory = psutil.virtual_memory()

        return (
            max(int(memory.total), 0),
            max(int(memory.available), 0),
        )

    def _storage(self) -> tuple[int, int]:
        try:
            usage = shutil.disk_usage(self.storage_path)
        except (OSError, ValueError):
            return 0, 0

        return (
            max(int(usage.total), 0),
            max(int(usage.free), 0),
        )
