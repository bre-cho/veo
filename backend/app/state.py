from app.services.production.timeline_repository import TimelineRepository
from app.services.production.timeline_service import ProductionTimelineService
from app.services.strategy.repository import InMemoryStrategyRepository
from app.services.strategy.strategy_service import EnterpriseStrategyService


timeline_repository = TimelineRepository()
timeline_service = ProductionTimelineService(timeline_repository)

strategy_repository = InMemoryStrategyRepository()
strategy_service = EnterpriseStrategyService(strategy_repository)
