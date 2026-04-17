from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


RenderProvider = Literal["veo_3_1"]


@dataclass(frozen=True)
class ProviderCapabilities:
    provider: RenderProvider
    label: str
    default_scene_duration_sec: float
    max_scene_duration_sec: float
    supports_native_audio: bool
    supports_multi_shot_prompt: bool
    recommended_mode: str


PROVIDER_CAPABILITIES: dict[RenderProvider, ProviderCapabilities] = {
    "veo_3_1": ProviderCapabilities(
        provider="veo_3_1",
        label="Google Veo 3.1",
        default_scene_duration_sec=8.0,
        max_scene_duration_sec=8.0,
        supports_native_audio=True,
        supports_multi_shot_prompt=False,
        recommended_mode="cinematic_single_shot",
    ),
}


def get_provider_capabilities(provider: RenderProvider) -> ProviderCapabilities:
    if provider not in PROVIDER_CAPABILITIES:
        raise ValueError(f"Unsupported provider: {provider}")
    return PROVIDER_CAPABILITIES[provider]
