from __future__ import annotations

from .types import PlannedScene, ProviderRenderPayload
from .veo_adapter import adapt_scene_to_veo


def build_provider_payload(scene: PlannedScene, provider: str) -> ProviderRenderPayload:
    if provider == "veo_3_1":
        return adapt_scene_to_veo(scene)

    raise ValueError(f"Unsupported provider: {provider}")