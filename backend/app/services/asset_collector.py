from pathlib import Path
import tempfile
from app.core.config import settings


def _resolve_render_cache_dir() -> Path:
    preferred = Path(settings.render_cache_dir)
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except (PermissionError, FileNotFoundError):
        fallback = Path(tempfile.gettempdir()) / "render-factory-storage" / "render_cache"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


RENDER_CACHE_DIR = _resolve_render_cache_dir()

async def cache_remote_video(job_id: str, scene_index: int, url: str) -> str:
    local_path = RENDER_CACHE_DIR / job_id / f"scene_{scene_index:03d}.mp4"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(b"")
    return str(local_path)
