"""Private no-experiment configuration layer for Alpine Private Vibe.

The full upstream configuration orchestrator retains this layer name and order,
but remote experiment variants are deliberately ignored and cannot influence any
prompt, model routing, or tool setting.
"""

from __future__ import annotations

from collections.abc import Mapping

from vibe.core.config.layer import ConfigLayer, RawConfig
from vibe.core.config.types import EMPTY_CONFIG_SNAPSHOT, LayerConfigSnapshot


class GrowthbookLayer(ConfigLayer[RawConfig]):
    NAME = "growthbook"

    def __init__(self, *, name: str = NAME) -> None:
        super().__init__(name=name)

    def set_variants(self, variants: Mapping[str, str]) -> None:
        """Discard all remote or cached experiment assignments."""
        del variants

    async def _check_trust(self) -> bool:
        return True

    async def _build_config_snapshot(self) -> LayerConfigSnapshot:
        return EMPTY_CONFIG_SNAPSHOT

    async def _save_to_store(self, _next_config: RawConfig) -> str:
        raise NotImplementedError("GrowthbookLayer is read-only")
