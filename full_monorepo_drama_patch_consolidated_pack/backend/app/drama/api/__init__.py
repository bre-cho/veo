
from app.drama.api.drama_admin import router as drama_admin_router
from app.drama.api.drama_arcs import router as drama_arcs_router
from app.drama.api.drama_characters import router as drama_characters_router
from app.drama.api.drama_compile import router as drama_compile_router
from app.drama.api.drama_memory import router as drama_memory_router
from app.drama.api.drama_relationships import router as drama_relationships_router
from app.drama.api.drama_scenes import router as drama_scenes_router
from app.drama.api.drama_state import router as drama_state_router

ALL_DRAMA_ROUTERS = [
    drama_characters_router,
    drama_relationships_router,
    drama_scenes_router,
    drama_compile_router,
    drama_arcs_router,
    drama_memory_router,
    drama_state_router,
    drama_admin_router,
]
