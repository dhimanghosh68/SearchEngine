from __future__ import annotations

from dataclasses import dataclass

from apps.api.platform.contracts import PlatformCapabilities


@dataclass(frozen=True)
class Runtime:
    capabilities: PlatformCapabilities
