"""avatar_registry — static in-process registry of known avatar definitions.

Add new avatars here or load them from a DB-backed registry at startup.
Each entry must match the AvatarIdentityProfile schema fields.
"""
from __future__ import annotations

from typing import Any

AVATAR_REGISTRY: dict[str, dict[str, Any]] = {
    "narrator_dark_doc_v1": {
        "avatar_id": "narrator_dark_doc_v1",
        "display_name": "Dark Documentary Narrator",
        "persona": (
            "A calm but unsettling narrator who reveals the hidden systems "
            "behind modern events, speaking as if they already know what comes next."
        ),
        "narrative_role": "narrator",
        "tone": "dark_systemic",
        "visual_style": "dark_documentary",
        "belief_system": "Invisible systems shape visible outcomes.",
        "market_code": "US",
        "content_goals": ["retention", "series_binge"],
        "topic_classes": ["ai", "system", "attention", "control", "documentary"],
        "reference_image_urls": [],
        "voice_profile": {
            "provider": "elevenlabs",
            "voice_id": None,
            "delivery_style": "slow_cinematic",
            "speaking_rate": 0.95,
            "pitch": 0.95,
            "intensity": 1.15,
        },
        "metadata": {
            "default_expression": "calm_unease",
            "brand_role": "flagship",
        },
    },
    "expert_clean_tech_v1": {
        "avatar_id": "expert_clean_tech_v1",
        "display_name": "Clean Tech Explainer",
        "persona": (
            "A precise expert voice that explains technical shifts with "
            "authority and clarity, never sensationalising."
        ),
        "narrative_role": "expert",
        "tone": "clean_authoritative",
        "visual_style": "high_tech_minimal",
        "belief_system": "Technology should be explained clearly and responsibly.",
        "market_code": "US",
        "content_goals": ["retention", "conversion"],
        "topic_classes": ["ai", "technology", "business"],
        "reference_image_urls": [],
        "voice_profile": {
            "provider": "elevenlabs",
            "voice_id": None,
            "delivery_style": "measured_expert",
            "speaking_rate": 1.0,
            "pitch": 1.0,
            "intensity": 1.0,
        },
        "metadata": {
            "default_expression": "composed_focus",
            "brand_role": "secondary",
        },
    },
    "storyteller_vn_v1": {
        "avatar_id": "storyteller_vn_v1",
        "display_name": "Vietnamese Story Narrator",
        "persona": (
            "A warm, culturally-tuned Vietnamese narrator who blends personal "
            "insight with systemic analysis."
        ),
        "narrative_role": "narrator",
        "tone": "warm_reflective",
        "visual_style": "clean_modern",
        "belief_system": "Stories connect people across contexts.",
        "market_code": "VN",
        "content_goals": ["retention", "series_binge", "conversion"],
        "topic_classes": ["culture", "business", "ai", "lifestyle"],
        "reference_image_urls": [],
        "voice_profile": {
            "provider": "elevenlabs",
            "voice_id": None,
            "delivery_style": "conversational",
            "speaking_rate": 1.0,
            "pitch": 1.05,
            "intensity": 1.0,
        },
        "metadata": {
            "default_expression": "curious_warm",
            "brand_role": "primary_vn",
        },
    },
}
