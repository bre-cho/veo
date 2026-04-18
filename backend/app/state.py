from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.production.timeline_repository import InMemoryTimelineRepository
from app.services.production.timeline_service import ProductionTimelineService
from app.services.strategy.repository import InMemoryStrategyRepository
from app.services.strategy.strategy_service import EnterpriseStrategyService


@dataclass
class AppState:
	"""In-memory compatibility state used by strategy helper services."""

	directives: list[Any] = field(default_factory=list)
	campaign_windows: dict[str, Any] = field(default_factory=dict)
	contract_slas: dict[str, Any] = field(default_factory=dict)


timeline_repository = InMemoryTimelineRepository()
timeline_service = ProductionTimelineService(timeline_repository)

strategy_repository = InMemoryStrategyRepository()
strategy_service = EnterpriseStrategyService(strategy_repository)
