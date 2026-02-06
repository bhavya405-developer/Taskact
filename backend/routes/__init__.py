# Routes package for TaskAct
from .auth import router as auth_router, init_auth_routes
from .users import router as users_router, init_users_routes
from .tasks import router as tasks_router, init_tasks_routes
from .attendance import router as attendance_router, init_attendance_routes
from .timesheets import router as timesheets_router, init_timesheets_routes
