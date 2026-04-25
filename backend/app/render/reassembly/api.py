from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.render.reassembly.chunk_bootstrapper import ChunkBootstrapper
from app.render.reassembly.schemas import SmartReassemblyRequest
from app.render.reassembly.smart_reassembly_service import SmartReassemblyService

router = APIRouter(prefix="/api/v1/render/reassembly", tags=["render-reassembly"])

_service = SmartReassemblyService()


@router.post("/smart")
def smart_reassembly(payload: SmartReassemblyRequest) -> Dict[str, Any]:
    """Rebuild the changed scene chunk and fast-concat the final episode MP4.

    If ``force_full_rebuild=true`` is set, every scene chunk is re-encoded.
    Otherwise only the changed scene is rebuilt and all existing chunks are
    reused.

    After a successful smart reassembly call the scene manifest will have
    ``status=smart_reassembled`` and ``needs_reassembly=false``.
    """
    try:
        return _service.reassemble(payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/bootstrap/{project_id}/{episode_id}")
def bootstrap_chunk_index(project_id: str, episode_id: str) -> Dict[str, Any]:
    """Bootstrap the chunk index for an episode after the first full assembly.

    Encodes every scene into a standalone MP4 chunk, writes ``chunk_path``
    and ``smart_reassembly_ready=true`` to each scene's manifest, and
    persists the ``chunk_index.json``.

    Once bootstrapped, subsequent rerenders can use ``POST /smart`` without
    setting ``force_full_rebuild=true``.
    """
    try:
        return ChunkBootstrapper().bootstrap_episode(project_id, episode_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
