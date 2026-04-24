from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.drama.models.drama_character_profile import DramaCharacterProfile
from app.drama.models.drama_character_state import DramaCharacterState
from app.drama.schemas.character import CharacterCreate, CharacterUpdate

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


_RULES_DIR = Path(__file__).resolve().parent.parent / "rules"
_ARCHETYPE_PRESETS_FILE = _RULES_DIR / "archetype_presets.yaml"


class CastService:
    """
    CRUD + bootstrap service for drama characters.

    Design constraints:
    - additive only
    - safe to run before scene analysis engine exists
    - can seed the user-provided archetypes as acting/behavior defaults
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_characters(self, project_id: UUID) -> list[DramaCharacterProfile]:
        stmt: Select[tuple[DramaCharacterProfile]] = (
            select(DramaCharacterProfile)
            .where(DramaCharacterProfile.project_id == project_id)
            .order_by(DramaCharacterProfile.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_character(self, character_id: UUID) -> DramaCharacterProfile | None:
        return self.db.get(DramaCharacterProfile, character_id)

    def create_character(self, payload: CharacterCreate) -> DramaCharacterProfile:
        data = payload.model_dump()
        profile = DramaCharacterProfile(**data)
        self.db.add(profile)
        self.db.flush()

        bootstrap = profile.bootstrap_state_payload()
        state = DramaCharacterState(
            character_id=profile.id,
            scene_id=None,
            update_reason="bootstrap_from_profile",
            **bootstrap,
        )
        self.db.add(state)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_character(self, character_id: UUID, payload: CharacterUpdate) -> DramaCharacterProfile | None:
        profile = self.get_character(character_id)
        if not profile:
            return None

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, key, value)

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def apply_archetype_preset(self, character_id: UUID, archetype_name: str) -> DramaCharacterProfile | None:
        """
        Merge preset seed into an existing profile.

        Important:
        - This is additive merge behavior, not total overwrite.
        - Uploaded archetypes such as Mentor / Manipulator / Rebel /
          WoundedObserver / Authority should live in archetype_presets.yaml.
        """
        profile = self.get_character(character_id)
        if not profile:
            return None

        preset = self._load_archetype_preset(archetype_name)
        if not preset:
            return profile

        profile.archetype = archetype_name
        profile.pressure_response = preset.get("pressure_response", profile.pressure_response)
        profile.acting_preset_seed = self._merge_dict(profile.acting_preset_seed, preset)
        profile.speech_pattern = self._merge_dict(profile.speech_pattern, self._extract_speech_fields(preset))
        profile.movement_pattern = self._merge_dict(profile.movement_pattern, self._extract_movement_fields(preset))
        profile.gaze_pattern = self._merge_dict(profile.gaze_pattern, self._extract_gaze_fields(preset))

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_latest_state(self, character_id: UUID) -> DramaCharacterState | None:
        stmt = (
            select(DramaCharacterState)
            .where(DramaCharacterState.character_id == character_id)
            .order_by(DramaCharacterState.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    @staticmethod
    def _merge_dict(base: dict[str, Any] | None, patch: dict[str, Any] | None) -> dict[str, Any]:
        merged: dict[str, Any] = dict(base or {})
        for key, value in (patch or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = CastService._merge_dict(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _load_archetype_preset(self, archetype_name: str) -> dict[str, Any]:
        if yaml is None or not _ARCHETYPE_PRESETS_FILE.exists():
            return {}
        with _ARCHETYPE_PRESETS_FILE.open("r", encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
        return content.get(archetype_name, {})

    @staticmethod
    def _extract_speech_fields(preset: dict[str, Any]) -> dict[str, Any]:
        speech_keys = {"tempo", "pause_pattern", "speech_rhythm", "voice", "speech_amount"}
        return {k: v for k, v in preset.items() if k in speech_keys}

    @staticmethod
    def _extract_movement_fields(preset: dict[str, Any]) -> dict[str, Any]:
        movement_keys = {"movement", "movement_density", "distance", "body_leads_words", "energy"}
        return {k: v for k, v in preset.items() if k in movement_keys}

    @staticmethod
    def _extract_gaze_fields(preset: dict[str, Any]) -> dict[str, Any]:
        gaze_keys = {"gaze", "gaze_pattern", "micro_expression"}
        return {k: v for k, v in preset.items() if k in gaze_keys}
