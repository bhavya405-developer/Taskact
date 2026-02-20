from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne
import os
import logging
import asyncio
import random
import string
import math
import httpx
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
import jwt
from passlib.context import CryptContext
import pandas as pd
import io
import resend

# Import route modules
from routes.auth import router as auth_router, init_auth_routes
from routes.users import router as users_router, init_users_routes
from routes.tasks import router as tasks_router, init_tasks_routes
from routes.attendance import router as attendance_router, init_attendance_routes
from routes.timesheets import router as timesheets_router, init_timesheets_routes
from routes.tenants import router as tenants_router, init_tenants_routes
from routes.projects import router as projects_router, init_projects_routes

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="TaskAct API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Resend email configuration
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enums
class TaskStatus(str, Enum):
    PENDING = "pending"
    ON_HOLD = "on_hold"
    OVERDUE = "overdue"
    COMPLETED = "completed"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class UserRole(str, Enum):
    PARTNER = "partner"
    ASSOCIATE = "associate"
    JUNIOR = "junior"
    INTERN = "intern"
    SUPER_ADMIN = "super_admin"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    role: UserRole
    password_hash: Optional[str] = None  # Don't return in API responses
    phone: Optional[str] = None
    department: Optional[str] = None
    hire_date: Optional[datetime] = None
    profile_picture_url: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    skills: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True

class UserCreate(BaseModel):
    name: str
    email: str
    role: UserRole
    password: str
    phone: Optional[str] = None
    department: Optional[str] = None
    hire_date: Optional[datetime] = None
    profile_picture_url: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    skills: Optional[str] = None
    bio: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    tenant_id: Optional[str] = None  # For multi-tenancy
    phone: Optional[str] = None
    department: Optional[str] = None
    hire_date: Optional[datetime] = None
    profile_picture_url: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    skills: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    active: bool

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    hire_date: Optional[datetime] = None
    profile_picture_url: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    skills: Optional[str] = None
    bio: Optional[str] = None

class PasswordResetRequest(BaseModel):
    user_id: str
    new_password: str

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    color: Optional[str] = None  # Hex color for UI
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    active: Optional[bool] = None

class Client(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    company_type: Optional[str] = None  # Corporation, LLC, Individual, etc.
    industry: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True

class ClientCreate(BaseModel):
    name: str
    company_type: Optional[str] = None
    industry: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    company_type: Optional[str] = None
    industry: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None

class BulkImportResult(BaseModel):
    success_count: int
    error_count: int
    errors: List[str]
    created_items: List[str]

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Forgot Password Models
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class ResetPasswordWithOTPRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

class OTPRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    otp: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    used: bool = False

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    message: str
    task_id: Optional[str] = None
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Attendance Models
class AttendanceType(str, Enum):
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"

class Attendance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    user_name: str
    type: AttendanceType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timestamp_ist: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None  # Reverse geocoded address
    is_within_geofence: Optional[bool] = None
    distance_from_office: Optional[float] = None  # in meters
    device_info: Optional[str] = None

class AttendanceCreate(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None  # GPS accuracy in meters
    device_info: Optional[str] = None

class GeofenceSettings(BaseModel):
    id: str = Field(default="geofence_settings")
    enabled: bool = False
    locations: List[dict] = Field(default_factory=list)  # Up to 5 locations
    radius_meters: float = 100  # Default 100 meters
    updated_by: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GeofenceLocation(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None

class GeofenceSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    locations: Optional[List[dict]] = None
    radius_meters: Optional[float] = None

class AttendanceRules(BaseModel):
    id: str = Field(default="attendance_rules")
    min_hours_full_day: float = 8.0  # Minimum hours for full day
    working_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5])  # Mon-Sat (0=Monday)
    updated_by: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AttendanceRulesUpdate(BaseModel):
    min_hours_full_day: Optional[float] = None
    working_days: Optional[List[int]] = None

class Holiday(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str  # YYYY-MM-DD format
    name: str
    is_paid: bool = True
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class HolidayCreate(BaseModel):
    date: str  # YYYY-MM-DD format
    name: str
    is_paid: bool = True

class PasswordVerifyRequest(BaseModel):
    password: str

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    category: Optional[str] = None
    assignee_id: Optional[str] = None  # Made optional for legacy data
    assignee_name: Optional[str] = None  # Made optional for legacy data
    creator_id: Optional[str] = None  # Made optional for legacy data
    creator_name: Optional[str] = None  # Made optional for legacy data
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    # Timesheet fields
    estimated_hours: Optional[float] = None  # Optional estimate when creating
    actual_hours: Optional[float] = None  # Required when completing task
    # Status change history - records all status changes with IST timestamps
    status_history: Optional[List[dict]] = None
    # Project reference
    project_id: Optional[str] = None
    project_name: Optional[str] = None

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    client_name: str
    category: str
    assignee_id: str
    creator_id: Optional[str] = None  # Optional - will be set to current user by backend
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None  # Optional time estimate

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None
    category: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    actual_hours: Optional[float] = None  # Required when completing task

# Helper functions
# IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    """Get current time in IST"""
    return datetime.now(IST)

def utc_to_ist(utc_dt):
    """Convert UTC datetime to IST"""
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(IST)

def format_ist_datetime(dt):
    """Format datetime as IST string"""
    if dt is None:
        return None
    ist_dt = utc_to_ist(dt) if dt.tzinfo != IST else dt
    return ist_dt.strftime('%d-%b-%Y %I:%M %p IST')

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS coordinates in meters using Haversine formula"""
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

async def reverse_geocode(latitude: float, longitude: float) -> Optional[str]:
    """Reverse geocode coordinates to address using OpenStreetMap Nominatim (free)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "json",
                    "addressdetails": 1
                },
                headers={
                    "User-Agent": "TaskAct/1.0 (Attendance System)"  # Required by Nominatim
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("display_name", None)
            else:
                logger.warning(f"Reverse geocoding failed: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Reverse geocoding error: {str(e)}")
        return None

async def get_geofence_settings():
    """Get geofence settings from database"""
    settings = await db.geofence_settings.find_one({"id": "geofence_settings"})
    if not settings:
        # Create default settings with empty locations array
        default_settings = {
            "id": "geofence_settings",
            "enabled": False,
            "locations": [],
            "radius_meters": 100.0,
            "updated_by": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.geofence_settings.insert_one(default_settings.copy())
        return default_settings
    return parse_from_mongo(settings)

def check_within_any_geofence(lat: float, lon: float, locations: list, radius: float, gps_accuracy: float = 0) -> tuple:
    """
    Check if coordinates are within any of the geofence locations.
    
    Args:
        lat, lon: User's GPS coordinates
        locations: List of office locations
        radius: Geofence radius in meters
        gps_accuracy: GPS accuracy in meters (adds tolerance to the check)
    
    Returns: (is_within, closest_distance, closest_location_name)
    """
    if not locations:
        return (None, None, None)
    
    closest_distance = float('inf')
    closest_location = None
    is_within = False
    
    # Add GPS accuracy as tolerance (but cap it at 50m to prevent abuse)
    # This accounts for GPS drift while preventing users from gaming the system
    tolerance = min(gps_accuracy, 50) if gps_accuracy else 0
    effective_radius = radius + tolerance
    
    for loc in locations:
        if loc.get("latitude") and loc.get("longitude"):
            distance = haversine_distance(lat, lon, loc["latitude"], loc["longitude"])
            if distance < closest_distance:
                closest_distance = distance
                closest_location = loc.get("name", "Unknown")
            if distance <= effective_radius:
                is_within = True
    
    return (is_within, round(closest_distance, 2) if closest_distance != float('inf') else None, closest_location)

def prepare_for_mongo(data):
    """Convert datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    """Parse MongoDB document for API response - handles ObjectId and datetime"""
    if isinstance(item, dict):
        # Remove MongoDB's _id field (ObjectId is not JSON serializable)
        if '_id' in item:
            del item['_id']
        # Parse datetime strings
        for key, value in item.items():
            if isinstance(value, str) and key.endswith(('_at', 'due_date', 'timestamp')):
                try:
                    item[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass
    return item

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": user_id, "active": True})
    if user is None:
        raise credentials_exception
    return UserResponse(**parse_from_mongo(user))

async def get_current_partner(current_user: UserResponse = Depends(get_current_user)):
    if current_user.role != UserRole.PARTNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only partners can perform this action"
        )
    return current_user

async def create_notification(user_id: str, title: str, message: str, task_id: str = None):
    """Create a notification for a user"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        task_id=task_id
    )
    notification_dict = prepare_for_mongo(notification.dict())
    await db.notifications.insert_one(notification_dict)
    return notification

def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))

async def send_otp_email(email: str, otp: str, user_name: str = "User") -> bool:
    """Send OTP email using Resend"""
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY not configured")
        return False
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Inter', Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px; }}
            .container {{ max-width: 480px; margin: 0 auto; background: white; border-radius: 8px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .logo {{ text-align: center; margin-bottom: 24px; }}
            .logo h1 {{ color: #4f46e5; font-size: 28px; margin: 0; }}
            .otp-box {{ background: #f0f9ff; border: 2px dashed #3b82f6; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0; }}
            .otp-code {{ font-size: 36px; font-weight: bold; color: #1e40af; letter-spacing: 8px; }}
            .message {{ color: #4b5563; line-height: 1.6; }}
            .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 24px; }}
            .warning {{ background: #fef3c7; border-radius: 6px; padding: 12px; margin-top: 16px; color: #92400e; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <h1>TaskAct</h1>
            </div>
            <p class="message">Hi {user_name},</p>
            <p class="message">You requested to reset your password. Use the OTP below to proceed:</p>
            <div class="otp-box">
                <div class="otp-code">{otp}</div>
            </div>
            <p class="message">This OTP is valid for <strong>10 minutes</strong>.</p>
            <div class="warning">
                If you didn't request this password reset, please ignore this email or contact support if you have concerns.
            </div>
            <div class="footer">
                <p>&copy; 2024 TaskAct. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    params = {
        "from": SENDER_EMAIL,
        "to": [email],
        "subject": "TaskAct - Password Reset OTP",
        "html": html_content
    }
    
    try:
        # Run sync SDK in thread to keep FastAPI non-blocking
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"OTP email sent to {email}, email_id: {result.get('id')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False

async def update_overdue_tasks(tenant_id: str = None):
    """Automatically update tasks to overdue status if past due date"""
    current_time = datetime.now(timezone.utc)
    
    # Build query - filter by tenant if provided
    query = {
        "status": TaskStatus.PENDING,
        "due_date": {"$ne": None}
    }
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    # Only check PENDING tasks for overdue - ON_HOLD tasks should stay on hold
    tasks = await db.tasks.find(query).to_list(length=5000)
    
    # Collect bulk operations for overdue tasks
    bulk_operations = []
    
    for task in tasks:
        due_date_value = task.get('due_date')
        if due_date_value:
            try:
                # Handle both datetime objects (MongoDB Atlas) and ISO strings (local MongoDB)
                if isinstance(due_date_value, datetime):
                    due_date = due_date_value
                elif isinstance(due_date_value, str):
                    due_date = datetime.fromisoformat(due_date_value.replace('Z', '+00:00'))
                else:
                    continue
                
                # Ensure timezone awareness for comparison
                if due_date.tzinfo is None:
                    due_date = due_date.replace(tzinfo=timezone.utc)
                
                # Check if task is actually overdue
                if due_date < current_time:
                    bulk_operations.append(
                        UpdateOne(
                            {"id": task["id"]},
                            {"$set": {
                                "status": TaskStatus.OVERDUE,
                                "updated_at": current_time.isoformat()
                            }}
                        )
                    )
            except Exception as e:
                # Log error but continue processing other tasks
                print(f"Error processing overdue task {task.get('id', 'unknown')}: {e}")
    
    # Execute bulk update if there are any overdue tasks
    updated_count = 0
    if bulk_operations:
        result = await db.tasks.bulk_write(bulk_operations)
        updated_count = result.modified_count
    
    return updated_count

# ==================== INITIALIZE ROUTE MODULES ====================
# Initialize auth routes with dependencies
init_auth_routes(
    _db=db,
    _secret_key=SECRET_KEY,
    _algorithm=ALGORITHM,
    _token_expire=ACCESS_TOKEN_EXPIRE_MINUTES,
    _user_role=UserRole,
    _user_response=UserResponse,
    _parse_mongo=parse_from_mongo,
    _prepare_mongo=prepare_for_mongo,
    _create_notification=create_notification,
    _logger=logger
)

# Initialize users routes with dependencies
init_users_routes(
    _db=db,
    _secret_key=SECRET_KEY,
    _algorithm=ALGORITHM,
    _user_role=UserRole,
    _user_response=UserResponse,
    _user_create=UserCreate,
    _user_profile_update=UserProfileUpdate,
    _password_reset_request=PasswordResetRequest,
    _parse_mongo=parse_from_mongo,
    _prepare_mongo=prepare_for_mongo,
    _create_notification=create_notification,
    _logger=logger
)

# Initialize tasks routes with dependencies
init_tasks_routes(
    _db=db,
    _secret_key=SECRET_KEY,
    _algorithm=ALGORITHM,
    _user_role=UserRole,
    _user_response=UserResponse,
    _task=Task,
    _task_create=TaskCreate,
    _task_update=TaskUpdate,
    _task_status=TaskStatus,
    _bulk_import_result=BulkImportResult,
    _password_verify_request=PasswordVerifyRequest,
    _parse_mongo=parse_from_mongo,
    _prepare_mongo=prepare_for_mongo,
    _create_notification=create_notification,
    _update_overdue_tasks=update_overdue_tasks,
    _get_ist_now=get_ist_now,
    _format_ist_datetime=format_ist_datetime,
    _logger=logger
)

# Initialize attendance routes with dependencies
init_attendance_routes(
    _db=db,
    _secret_key=SECRET_KEY,
    _algorithm=ALGORITHM,
    _user_role=UserRole,
    _user_response=UserResponse,
    _attendance_type=AttendanceType,
    _attendance_create=AttendanceCreate,
    _geofence_settings_update=GeofenceSettingsUpdate,
    _attendance_rules_update=AttendanceRulesUpdate,
    _holiday_create=HolidayCreate,
    _parse_mongo=parse_from_mongo,
    _prepare_mongo=prepare_for_mongo,
    _create_notification=create_notification,
    _get_geofence_settings=get_geofence_settings,
    _check_within_any_geofence=check_within_any_geofence,
    _reverse_geocode=reverse_geocode,
    _format_ist_datetime=format_ist_datetime,
    _logger=logger
)

# Initialize timesheets routes with dependencies
init_timesheets_routes(
    _db=db,
    _secret_key=SECRET_KEY,
    _algorithm=ALGORITHM,
    _user_role=UserRole,
    _user_response=UserResponse,
    _task_status=TaskStatus,
    _parse_mongo=parse_from_mongo,
    _logger=logger
)

# Initialize tenants routes with dependencies
init_tenants_routes(
    _db=db,
    _secret_key=SECRET_KEY,
    _algorithm=ALGORITHM,
    _token_expire=ACCESS_TOKEN_EXPIRE_MINUTES,
    _parse_mongo=parse_from_mongo,
    _prepare_mongo=prepare_for_mongo,
    _logger=logger
)

# Initialize projects routes with dependencies
init_projects_routes(
    _db=db,
    _secret_key=SECRET_KEY,
    _algorithm=ALGORITHM,
    _user_role=UserRole,
    _user_response=UserResponse,
    _task_status=TaskStatus,
    _parse_mongo=parse_from_mongo,
    _prepare_mongo=prepare_for_mongo,
    _logger=logger
)

# Notification endpoints
@api_router.get("/notifications", response_model=List[Notification])
async def get_user_notifications(current_user: UserResponse = Depends(get_current_user)):
    notifications = await db.notifications.find(
        {"user_id": current_user.id}
    ).sort("created_at", -1).limit(20).to_list(length=5000)
    return [Notification(**parse_from_mongo(notification)) for notification in notifications]

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: UserResponse = Depends(get_current_user)):
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"read": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}

@api_router.put("/notifications/mark-all-read")
async def mark_all_notifications_as_read(current_user: UserResponse = Depends(get_current_user)):
    """Mark all notifications as read for the current user"""
    result = await db.notifications.update_many(
        {"user_id": current_user.id, "read": False},
        {"$set": {"read": True}}
    )
    return {"message": f"Marked {result.modified_count} notifications as read", "modified_count": result.modified_count}

@api_router.get("/notifications/unread-count")
async def get_unread_notification_count(current_user: UserResponse = Depends(get_current_user)):
    count = await db.notifications.count_documents({"user_id": current_user.id, "read": False})
    return {"unread_count": count}

# Category Management endpoints (Partners only)
@api_router.post("/categories", response_model=Category)
async def create_category(category_data: CategoryCreate, current_user: UserResponse = Depends(get_current_partner)):
    # Check if category name already exists
    existing_category = await db.categories.find_one({"name": category_data.name, "active": True})
    if existing_category:
        raise HTTPException(status_code=400, detail="Category name already exists")
    
    category_dict = category_data.dict()
    category_dict["created_by"] = current_user.id
    category = Category(**category_dict)
    
    category_dict = prepare_for_mongo(category.dict())
    await db.categories.insert_one(category_dict)
    return category

# Category Template and Bulk Import endpoints (Partners only) - Must come before parameterized routes
@api_router.get("/categories/download-template")
async def download_categories_template(current_user: UserResponse = Depends(get_current_partner)):
    """Download Excel template for bulk category import"""
    
    # Create sample data with headers
    template_data = {
        'Name': ['Legal Research', 'Contract Review', 'Client Meeting'],
        'Description': [
            'Research legal precedents and case law',
            'Review and analyze legal contracts',
            'Meetings and consultations with clients'
        ],
        'Color': ['#3B82F6', '#10B981', '#F59E0B']
    }
    
    df = pd.DataFrame(template_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Write data
        df.to_excel(writer, sheet_name='Categories', index=False)
        
        # Get workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Categories']
        
        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F46E5',
            'font_color': 'white',
            'border': 1
        })
        
        # Format headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Add instructions sheet
        instructions_data = {
            'Instructions': [
                '1. Fill in the category information below',
                '2. Name: Required field - unique category name',
                '3. Description: Optional - brief description of the category',
                '4. Color: Optional - hex color code (e.g., #3B82F6)',
                '5. Save the file and upload it back to import',
                '',
                'Sample Colors:',
                'Blue: #3B82F6',
                'Green: #10B981', 
                'Amber: #F59E0B',
                'Red: #EF4444',
                'Purple: #8B5CF6'
            ]
        }
        instructions_df = pd.DataFrame(instructions_data)
        instructions_df.to_excel(writer, sheet_name='Instructions', index=False)
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=categories_template.xlsx"}
    )

@api_router.get("/categories", response_model=List[Category])
async def get_categories(current_user: UserResponse = Depends(get_current_user)):
    # Filter by tenant_id
    query = {"active": True}
    if current_user.tenant_id:
        query["tenant_id"] = current_user.tenant_id
    categories = await db.categories.find(query).sort("name", 1).to_list(length=5000)
    return [Category(**parse_from_mongo(category)) for category in categories]

@api_router.get("/categories/{category_id}", response_model=Category)
async def get_category(category_id: str, current_user: UserResponse = Depends(get_current_user)):
    query = {"id": category_id, "active": True}
    if current_user.tenant_id:
        query["tenant_id"] = current_user.tenant_id
    category = await db.categories.find_one(query)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return Category(**parse_from_mongo(category))

@api_router.put("/categories/{category_id}", response_model=Category)
async def update_category(
    category_id: str, 
    category_update: CategoryUpdate, 
    current_user: UserResponse = Depends(get_current_partner)
):
    query = {"id": category_id, "active": True}
    if current_user.tenant_id:
        query["tenant_id"] = current_user.tenant_id
    existing_category = await db.categories.find_one(query)
    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = {k: v for k, v in category_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Check if name is being changed and if it already exists for this tenant
    if "name" in update_data and update_data["name"] != existing_category["name"]:
        name_query = {"name": update_data["name"], "active": True}
        if current_user.tenant_id:
            name_query["tenant_id"] = current_user.tenant_id
        existing_name = await db.categories.find_one(name_query)
        if existing_name:
            raise HTTPException(status_code=400, detail="Category name already exists")
    
    result = await db.categories.update_one({"id": category_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    
    updated_category = await db.categories.find_one({"id": category_id})
    return Category(**parse_from_mongo(updated_category))

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, current_user: UserResponse = Depends(get_current_partner)):
    # Check if category is in use by any tasks for this tenant
    task_query = {"category": category_id}
    if current_user.tenant_id:
        task_query["tenant_id"] = current_user.tenant_id
    tasks_using_category = await db.tasks.count_documents(task_query)
    if tasks_using_category > 0:
        raise HTTPException(status_code=400, detail="Cannot delete category that is in use by tasks")
    
    result = await db.categories.update_one({"id": category_id}, {"$set": {"active": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted successfully"}

# Duplicate removed - template download moved earlier to fix routing

@api_router.post("/categories/bulk-import", response_model=BulkImportResult)
async def bulk_import_categories(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_partner)
):
    """Bulk import categories from Excel/CSV file"""
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="File must be Excel (.xlsx, .xls) or CSV (.csv)")
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse file based on extension
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(content), sheet_name='Categories')
        
        # Validate required columns
        required_columns = ['Name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        success_count = 0
        error_count = 0
        errors = []
        created_items = []
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row['Name']) or row['Name'].strip() == '':
                    continue
                
                category_name = row['Name'].strip()
                
                # Check if category already exists
                existing = await db.categories.find_one({"name": category_name, "active": True})
                if existing:
                    errors.append(f"Row {index + 2}: Category '{category_name}' already exists")
                    error_count += 1
                    continue
                
                # Create category
                category_data = {
                    "name": category_name,
                    "description": row.get('Description', '').strip() if pd.notna(row.get('Description')) else None,
                    "color": row.get('Color', '#3B82F6').strip() if pd.notna(row.get('Color')) else '#3B82F6'
                }
                
                category_dict = category_data.copy()
                category_dict["id"] = str(uuid.uuid4())
                category_dict["created_by"] = current_user.id
                category_dict["created_at"] = datetime.now(timezone.utc)
                category_dict["active"] = True
                
                category_dict = prepare_for_mongo(category_dict)
                await db.categories.insert_one(category_dict)
                
                success_count += 1
                created_items.append(category_name)
                
            except Exception as e:
                error_count += 1
                errors.append(f"Row {index + 2}: {str(e)}")
        
        return BulkImportResult(
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            created_items=created_items
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

# Client Management endpoints (Partners only)
@api_router.post("/clients", response_model=Client)
async def create_client(client_data: ClientCreate, current_user: UserResponse = Depends(get_current_partner)):
    # Check if client name already exists
    existing_client = await db.clients.find_one({"name": client_data.name, "active": True})
    if existing_client:
        raise HTTPException(status_code=400, detail="Client name already exists")
    
    client_dict = client_data.dict()
    client_dict["created_by"] = current_user.id
    client = Client(**client_dict)
    
    client_dict = prepare_for_mongo(client.dict())
    await db.clients.insert_one(client_dict)
    return client

# Client Template and Bulk Import endpoints (Partners only) - Must come before parameterized routes
@api_router.get("/clients/download-template")
async def download_clients_template(current_user: UserResponse = Depends(get_current_partner)):
    """Download Excel template for bulk client import"""
    
    # Create sample data - only Name is required, others are optional
    template_data = {
        'Name *': ['TechCorp Inc.', 'Global Manufacturing Ltd.', 'Healthcare Solutions Group', 'Simple Client'],
        'Company Type': ['Corporation', 'Corporation', 'LLC', ''],
        'Industry': ['Technology', 'Manufacturing', 'Healthcare', ''],
        'Contact Person': ['John Smith', 'Maria Rodriguez', 'Dr. James Wilson', ''],
        'Email': ['john@techcorp.com', 'maria@global.com', 'james@healthcare.com', ''],
        'Phone': ['+1 (555) 123-4567', '+1 (555) 987-6543', '+1 (555) 456-7890', ''],
        'Address': [
            '123 Tech Street, Silicon Valley, CA 94000',
            '456 Industrial Blvd, Detroit, MI 48000',
            '789 Medical Center Dr, Boston, MA 02000',
            ''
        ],
        'Notes': [
            'Major technology client',
            'Large manufacturing company',
            'Healthcare consulting firm',
            ''
        ]
    }
    
    df = pd.DataFrame(template_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Write data
        df.to_excel(writer, sheet_name='Clients', index=False)
        
        # Get workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Clients']
        
        # Add formatting - required field header in different color
        required_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#DC2626',
            'font_color': 'white',
            'border': 1
        })
        
        optional_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#059669',
            'font_color': 'white',
            'border': 1
        })
        
        # Format headers - first column (Name) is required, rest are optional
        for col_num, value in enumerate(df.columns.values):
            if col_num == 0:  # Name column - required
                worksheet.write(0, col_num, value, required_header_format)
            else:
                worksheet.write(0, col_num, value, optional_header_format)
        
        # Set column widths
        worksheet.set_column('A:A', 30)  # Name
        worksheet.set_column('B:B', 15)  # Company Type
        worksheet.set_column('C:C', 15)  # Industry
        worksheet.set_column('D:D', 20)  # Contact Person
        worksheet.set_column('E:E', 25)  # Email
        worksheet.set_column('F:F', 18)  # Phone
        worksheet.set_column('G:G', 40)  # Address
        worksheet.set_column('H:H', 30)  # Notes
        
        # Add instructions sheet
        instructions_data = {
            'Instructions': [
                'HOW TO IMPORT CLIENTS',
                '=====================',
                '',
                'REQUIRED FIELD (marked with * in red):',
                '  - Name: Unique client name (REQUIRED)',
                '',
                'OPTIONAL FIELDS (marked in green):',
                '  - Company Type: Corporation, LLC, Partnership, Individual, etc.',
                '  - Industry: Technology, Healthcare, Finance, Manufacturing, etc.',
                '  - Contact Person: Primary contact name',
                '  - Email: Client email address',
                '  - Phone: Client phone number',
                '  - Address: Full address including city, state, zip',
                '  - Notes: Additional information about the client',
                '',
                'SIMPLE IMPORT EXAMPLE:',
                '  You can import clients with just the Name column.',
                '  See row 5 in the Clients sheet for an example.',
                '',
                'STEPS:',
                '  1. Add client names in the "Name *" column',
                '  2. Fill in optional fields as needed (or leave blank)',
                '  3. Delete the sample rows (rows 2-5)',
                '  4. Save the file',
                '  5. Upload the file to import clients'
            ]
        }
        instructions_df = pd.DataFrame(instructions_data)
        instructions_df.to_excel(writer, sheet_name='Instructions', index=False)
        
        # Format instructions sheet
        instr_worksheet = writer.sheets['Instructions']
        instr_worksheet.set_column('A:A', 60)
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=clients_template.xlsx"}
    )

@api_router.get("/clients", response_model=List[Client])
async def get_clients(current_user: UserResponse = Depends(get_current_user)):
    # Filter by tenant_id
    query = {"active": True}
    if current_user.tenant_id:
        query["tenant_id"] = current_user.tenant_id
    clients = await db.clients.find(query).sort("name", 1).to_list(length=5000)
    return [Client(**parse_from_mongo(client)) for client in clients]

@api_router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str, current_user: UserResponse = Depends(get_current_user)):
    query = {"id": client_id, "active": True}
    if current_user.tenant_id:
        query["tenant_id"] = current_user.tenant_id
    client = await db.clients.find_one(query)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return Client(**parse_from_mongo(client))

@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(
    client_id: str, 
    client_update: ClientUpdate, 
    current_user: UserResponse = Depends(get_current_partner)
):
    query = {"id": client_id, "active": True}
    if current_user.tenant_id:
        query["tenant_id"] = current_user.tenant_id
    existing_client = await db.clients.find_one(query)
    if not existing_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = {k: v for k, v in client_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Check if name is being changed and if it already exists for this tenant
    if "name" in update_data and update_data["name"] != existing_client["name"]:
        name_query = {"name": update_data["name"], "active": True}
        if current_user.tenant_id:
            name_query["tenant_id"] = current_user.tenant_id
        existing_name = await db.clients.find_one(name_query)
        if existing_name:
            raise HTTPException(status_code=400, detail="Client name already exists")
    
    result = await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    updated_client = await db.clients.find_one({"id": client_id})
    return Client(**parse_from_mongo(updated_client))

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: UserResponse = Depends(get_current_partner)):
    # Check if client is in use by any tasks
    tasks_using_client = await db.tasks.count_documents({"client_name": client_id})
    if tasks_using_client > 0:
        raise HTTPException(status_code=400, detail="Cannot delete client that is in use by tasks")
    
    result = await db.clients.update_one({"id": client_id}, {"$set": {"active": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}

# Duplicate removed - template download moved earlier to fix routing

@api_router.post("/clients/bulk-import", response_model=BulkImportResult)
async def bulk_import_clients(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_partner)
):
    """Bulk import clients from Excel/CSV file"""
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="File must be Excel (.xlsx, .xls) or CSV (.csv)")
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse file based on extension
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(content), sheet_name='Clients')
        
        # Check for Name column (with or without *)
        name_column = None
        for col in df.columns:
            if col.strip().lower().replace('*', '').strip() == 'name':
                name_column = col
                break
        
        if not name_column:
            raise HTTPException(
                status_code=400, 
                detail="Missing required column: 'Name' (or 'Name *')"
            )
        
        success_count = 0
        error_count = 0
        errors = []
        created_items = []
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row[name_column]) or str(row[name_column]).strip() == '':
                    continue
                
                client_name = str(row[name_column]).strip()
                
                # Check if client already exists
                existing = await db.clients.find_one({"name": client_name, "active": True})
                if existing:
                    errors.append(f"Row {index + 2}: Client '{client_name}' already exists")
                    error_count += 1
                    continue
                
                # Helper function to get optional field value
                def get_optional(field_name):
                    value = row.get(field_name)
                    if pd.isna(value) or str(value).strip() == '':
                        return None
                    return str(value).strip()
                
                # Create client - only Name is required
                client_dict = {
                    "id": str(uuid.uuid4()),
                    "name": client_name,
                    "company_type": get_optional('Company Type'),
                    "industry": get_optional('Industry'),
                    "contact_person": get_optional('Contact Person'),
                    "email": get_optional('Email'),
                    "phone": get_optional('Phone'),
                    "address": get_optional('Address'),
                    "notes": get_optional('Notes'),
                    "created_by": current_user.id,
                    "created_at": datetime.now(timezone.utc),
                    "active": True
                }
                
                client_dict = prepare_for_mongo(client_dict)
                await db.clients.insert_one(client_dict)
                
                success_count += 1
                created_items.append(client_name)
                
            except Exception as e:
                error_count += 1
                errors.append(f"Row {index + 2}: {str(e)}")
        
        return BulkImportResult(
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            created_items=created_items
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

async def get_filters(current_user: UserResponse = Depends(get_current_user)):
    # Build query based on user role
    query = {}
    if current_user.role != UserRole.PARTNER:
        query["assignee_id"] = current_user.id
    
    # Get unique client names
    clients = await db.tasks.distinct("client_name", query)
    
    # Get unique categories
    categories = await db.tasks.distinct("category", query)
    
    return {
        "clients": sorted([client for client in clients if client]),
        "categories": sorted([category for category in categories if category])
    }

# Dashboard endpoint
@api_router.get("/dashboard")
async def get_dashboard(current_user: UserResponse = Depends(get_current_user)):
    # Build query based on user role - ALWAYS include tenant_id filter
    tenant_filter = {"tenant_id": current_user.tenant_id} if current_user.tenant_id else {}
    
    task_query = {**tenant_filter}
    if current_user.role != UserRole.PARTNER:
        task_query["assignee_id"] = current_user.id
    
    # Update overdue tasks before getting counts (only for this tenant)
    await update_overdue_tasks(current_user.tenant_id)
    
    # Get counts by status
    pending_count = await db.tasks.count_documents({**task_query, "status": TaskStatus.PENDING})
    on_hold_count = await db.tasks.count_documents({**task_query, "status": TaskStatus.ON_HOLD})
    completed_count = await db.tasks.count_documents({**task_query, "status": TaskStatus.COMPLETED})
    overdue_count = await db.tasks.count_documents({**task_query, "status": TaskStatus.OVERDUE})
    
    # Get overdue tasks (all for partners, own for others)
    overdue_tasks = await db.tasks.find({**task_query, "status": TaskStatus.OVERDUE}).sort("due_date", 1).to_list(length=5000)
    
    # Get tasks due in next 7 days (PENDING only, exclude OVERDUE)
    today = datetime.now(timezone.utc)
    seven_days_later = today + timedelta(days=7)
    
    due_7_days_query = {
        **task_query,
        "status": TaskStatus.PENDING,  # Only pending tasks, not overdue
        "due_date": {"$lte": seven_days_later.isoformat(), "$gte": today.strftime("%Y-%m-%d")}
    }
    due_7_days_tasks = await db.tasks.find(due_7_days_query).sort("due_date", 1).to_list(length=5000)
    
    # For backward compatibility, also include recent_tasks
    recent_tasks = overdue_tasks + due_7_days_tasks
    
    # Get team performance (only for partners) - filter by tenant_id
    team_stats = []
    if current_user.role == UserRole.PARTNER:
        users = await db.users.find({**tenant_filter, "active": True}).to_list(length=5000)
        
        for user in users:
            user_tasks = await db.tasks.count_documents({**tenant_filter, "assignee_id": user["id"]})
            completed_tasks = await db.tasks.count_documents({**tenant_filter, "assignee_id": user["id"], "status": TaskStatus.COMPLETED})
            
            team_stats.append({
                "user_id": user["id"],
                "name": user["name"],
                "role": user["role"],
                "total_tasks": user_tasks,
                "completed_tasks": completed_tasks,
                "completion_rate": (completed_tasks / user_tasks * 100) if user_tasks > 0 else 0
            })
    
    # Get client analytics (only for partners) - filter by tenant_id
    client_stats = []
    if current_user.role == UserRole.PARTNER:
        # Get distinct clients for this tenant only
        client_tasks_cursor = db.tasks.find(tenant_filter, {"client_name": 1})
        client_names = set()
        async for task in client_tasks_cursor:
            if task.get("client_name"):
                client_names.add(task["client_name"])
        
        for client in list(client_names)[:5]:  # Top 5 clients
            client_tasks = await db.tasks.count_documents({**tenant_filter, "client_name": client})
            completed_client_tasks = await db.tasks.count_documents({**tenant_filter, "client_name": client, "status": TaskStatus.COMPLETED})
            client_stats.append({
                "client_name": client,
                "total_tasks": client_tasks,
                "completed_tasks": completed_client_tasks,
                "completion_rate": (completed_client_tasks / client_tasks * 100) if client_tasks > 0 else 0
            })
    
    # Get category analytics (only for partners) - filter by tenant_id
    category_stats = []
    if current_user.role == UserRole.PARTNER:
        # Get distinct categories for this tenant only
        cat_tasks_cursor = db.tasks.find(tenant_filter, {"category": 1})
        categories = set()
        async for task in cat_tasks_cursor:
            if task.get("category"):
                categories.add(task["category"])
        
        for category in categories:
            category_tasks = await db.tasks.count_documents({**tenant_filter, "category": category})
            category_stats.append({
                "category": category,
                "task_count": category_tasks
            })
    
    return {
        "task_counts": {
            "pending": pending_count,
            "on_hold": on_hold_count,
            "completed": completed_count,
            "overdue": overdue_count,
            "total": pending_count + on_hold_count + completed_count + overdue_count
        },
        "recent_tasks": [Task(**parse_from_mongo(task)) for task in recent_tasks],
        "overdue_tasks": [Task(**parse_from_mongo(task)) for task in overdue_tasks],
        "due_7_days_tasks": [Task(**parse_from_mongo(task)) for task in due_7_days_tasks],
        "team_stats": team_stats,  # Empty for non-partners
        "client_stats": sorted(client_stats, key=lambda x: x["total_tasks"], reverse=True) if client_stats else [],
        "category_stats": sorted(category_stats, key=lambda x: x["task_count"], reverse=True) if category_stats else []
    }

# Health check
@api_router.get("/")
async def root():
    return {"message": "TaskAct API is running"}

# Include routers in the main app
app.include_router(api_router)
app.include_router(auth_router, prefix="/api")  # Auth routes from routes/auth.py
app.include_router(users_router, prefix="/api")  # Users routes
app.include_router(tasks_router, prefix="/api")  # Tasks routes
app.include_router(attendance_router, prefix="/api")  # Attendance routes
app.include_router(timesheets_router, prefix="/api")  # Timesheets routes
app.include_router(tenants_router, prefix="/api")  # Tenants routes (Multi-tenant)
app.include_router(projects_router, prefix="/api")  # Projects routes

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()