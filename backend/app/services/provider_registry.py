from __future__ import annotations

from app.providers.base import BaseVideoProviderAdapter
from app.providers.veo.adapter import VeoAdapter


def get_provider_adapter(provider: str) -> BaseVideoProviderAdapter:
    providers: dict[str, BaseVideoProviderAdapter] = {
        "veo": VeoAdapter(),
    }
    try:
        return providers[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported provider: {provider}") from exc