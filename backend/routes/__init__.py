# Routes package for TaskAct
# Re-export routers and init functions for use in server.py

__all__ = [
    'auth_router', 'init_auth_routes',
    'users_router', 'init_users_routes',
    'tasks_router', 'init_tasks_routes',
    'attendance_router', 'init_attendance_routes',
    'timesheets_router', 'init_timesheets_routes',
    'tenants_router', 'init_tenants_routes',
]

from .auth import router as auth_router
from .auth import init_auth_routes
from .users import router as users_router
from .users import init_users_routes
from .tasks import router as tasks_router
from .tasks import init_tasks_routes
from .attendance import router as attendance_router
from .attendance import init_attendance_routes
from .timesheets import router as timesheets_router
from .timesheets import init_timesheets_routes
from .tenants import router as tenants_router
from .tenants import init_tenants_routes
