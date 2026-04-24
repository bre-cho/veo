"""Drama model registry.

This file intentionally imports all SQLAlchemy models so Alembic can discover
Drama tables through Base.metadata when env.py imports app.models or this module.
"""

from app.drama.models.arc_progress import DramaArcProgress
from app.drama.models.drama_character_profile import DramaCharacterProfile
from app.drama.models.drama_character_state import DramaCharacterState
from app.drama.models.drama_relationship_edge import DramaRelationshipEdge
from app.drama.models.memory_trace import DramaMemoryTrace
from app.drama.models.scene_drama_state import DramaSceneState

__all__ = [
    "DramaArcProgress",
    "DramaCharacterProfile",
    "DramaCharacterState",
    "DramaRelationshipEdge",
    "DramaMemoryTrace",
    "DramaSceneState",
]
