"""
Zeno Platform — Dummy Provider (no-op fallback)
Used when no platform provider can be detected.
"""

from zeno.platform.providers.base import PlatformProvider, PlatformCaps


class DummyProvider(PlatformProvider):
    name = "dummy"

    @property
    def caps(self) -> PlatformCaps:
        return PlatformCaps()
