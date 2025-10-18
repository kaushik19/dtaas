from .connectors import router as connectors_router
from .tasks import router as tasks_router
from .dashboard import router as dashboard_router

__all__ = ['connectors_router', 'tasks_router', 'dashboard_router']

