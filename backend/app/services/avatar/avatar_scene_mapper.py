"""avatar_scene_mapper — injects avatar context into individual scene dicts.

The scene dict (canonical contract) gains a ``metadata.avatar_*`` sub-tree
that the prompt builder and render dispatch layer can read to:
- inject persona into the prompt text
- set reference_image_urls
- pass voice settings to the TTS provider
- enforce continuity constraints per scene

The input scene dict is never mutated; a shallow copy is returned.
"""
from __future__ import annotations

from typing import Any


class AvatarSceneMapper:
    """Merges avatar identity, voice, and continuity data into a scene dict."""

    def apply_to_scene(
        self,
        *,
        scene: dict[str, Any],
        avatar_identity: dict[str, Any],
        avatar_voice: dict[str, Any],
        avatar_continuity: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a new scene dict with avatar context embedded in metadata.

        Parameters
        ----------
        scene:
            Canonical scene dict (see project_render_runtime.py contract).
        avatar_identity:
            Avatar identity dict from the registry / AvatarSelectionResult.identity.
        avatar_voice:
            Resolved voice dict from AvatarVoiceEngine.resolve_voice_context().
        avatar_continuity:
            Serialisable continuity dict (AvatarContinuityState.model_dump()).
        """
        updated = dict(scene)
        metadata: dict[str, Any] = dict(updated.get("metadata") or {})

        metadata.update(
            {
                "avatar_id": avatar_identity.get("avatar_id"),
                "avatar_display_name": avatar_identity.get("display_name"),
                "avatar_persona": avatar_identity.get("persona"),
                "avatar_narrative_role": avatar_identity.get("narrative_role"),
                "avatar_tone": avatar_identity.get("tone"),
                "avatar_visual_style": avatar_identity.get("visual_style"),
                "avatar_voice_profile": avatar_voice,
                "avatar_continuity": avatar_continuity,
                # reference images forwarded to render dispatch
                "avatar_reference_image_urls": avatar_identity.get(
                    "reference_image_urls", []
                ),
            }
        )

        updated["metadata"] = metadata
        return updated

    def apply_to_scenes(
        self,
        *,
        scenes: list[dict[str, Any]],
        avatar_identity: dict[str, Any],
        avatar_voice: dict[str, Any],
        avatar_continuity: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Apply avatar context to an entire list of scene dicts."""
        return [
            self.apply_to_scene(
                scene=scene,
                avatar_identity=avatar_identity,
                avatar_voice=avatar_voice,
                avatar_continuity=avatar_continuity,
            )
            for scene in scenes
        ]
