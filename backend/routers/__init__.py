from .connectors import router as connectors_router
from .tasks import router as tasks_router
from .dashboard import router as dashboard_router
from .variables import router as variables_router
from .database_browser import router as database_browser_router

__all__ = ['connectors_router', 'tasks_router', 'dashboard_router', 'variables_router', 'database_browser_router']

