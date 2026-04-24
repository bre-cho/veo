
"""Multi-character drama engine package.

Consolidated additive patch for:
- character psychology state
- directional relationship graph
- scene analysis and render-bridge compilation
- continuity, memory, arc persistence, and worker orchestration
- read/query/admin/ops APIs

Integration note:
Adapt DB/session/router imports to the target monorepo without rewriting render core.
"""

__all__ = [
    "api",
    "engines",
    "models",
    "ops",
    "rules",
    "schemas",
    "services",
    "workers",
]
