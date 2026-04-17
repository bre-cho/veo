from __future__ import annotations

_PROVIDER_ALIASES: dict[str, str] = {
    "veo": "veo",
    "veo_3": "veo",
    "veo_3_1": "veo",
    "google_veo": "veo",
}


def normalize_provider_name(provider: str) -> str:
    """Return the canonical provider key for the given raw provider string.

    Aliases such as ``veo_3`` and ``veo_3_1`` are collapsed to the canonical
    form ``veo``.  Unknown values are returned lower-cased without modification
    so callers can decide how to handle unsupported providers.
    """
    value = provider.strip().lower()
    return _PROVIDER_ALIASES.get(value, value)
