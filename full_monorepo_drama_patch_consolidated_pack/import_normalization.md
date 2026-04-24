
# Import Normalization Guide

Use these canonical imports inside the drama package after merge:

## Infra imports to adapt per repo
- `from app.api.deps import get_db`
- `from app.db.base_class import Base`
- `from app.db.session import SessionLocal`

## Preferred package imports
- `from app.drama.models import ...`
- `from app.drama.schemas import ...`
- `from app.drama.services import ...`
- `from app.drama.engines import ...`
- `from app.drama.api import ALL_DRAMA_ROUTERS`

## Rule
Keep business-layer imports under `app.drama.*` stable.
Rewrite only infra boundary imports when adapting to the target monorepo.
