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
from tempfile import NamedTemporaryFile
import resend

# Import route modules
from routes.auth import router as auth_router, init_auth_routes
from routes.users import router as users_router, init_users_routes
from routes.tasks import router as tasks_router, init_tasks_routes
from routes.attendance import router as attendance_router, init_attendance_routes
from routes.timesheets import router as timesheets_router, init_timesheets_routes

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
    assignee_id: str
    assignee_name: str
    creator_id: str
    creator_name: str
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

async def update_overdue_tasks():
    """Automatically update tasks to overdue status if past due date"""
    current_time = datetime.now(timezone.utc)
    
    # Get all pending and on_hold tasks with due dates (with reasonable limit)
    tasks = await db.tasks.find({
        "status": {"$in": [TaskStatus.PENDING, TaskStatus.ON_HOLD]},
        "due_date": {"$ne": None}
    }).to_list(length=5000)
    
    # Collect bulk operations for overdue tasks
    bulk_operations = []
    
    for task in tasks:
        due_date_str = task.get('due_date')
        if due_date_str:
            try:
                # Parse the due date string to datetime object
                due_date = datetime.fromisoformat(due_date_str)
                
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
    categories = await db.categories.find({"active": True}).sort("name", 1).to_list(length=5000)
    return [Category(**parse_from_mongo(category)) for category in categories]

@api_router.get("/categories/{category_id}", response_model=Category)
async def get_category(category_id: str, current_user: UserResponse = Depends(get_current_user)):
    category = await db.categories.find_one({"id": category_id, "active": True})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return Category(**parse_from_mongo(category))

@api_router.put("/categories/{category_id}", response_model=Category)
async def update_category(
    category_id: str, 
    category_update: CategoryUpdate, 
    current_user: UserResponse = Depends(get_current_partner)
):
    existing_category = await db.categories.find_one({"id": category_id, "active": True})
    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = {k: v for k, v in category_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Check if name is being changed and if it already exists
    if "name" in update_data and update_data["name"] != existing_category["name"]:
        existing_name = await db.categories.find_one({"name": update_data["name"], "active": True})
        if existing_name:
            raise HTTPException(status_code=400, detail="Category name already exists")
    
    result = await db.categories.update_one({"id": category_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    
    updated_category = await db.categories.find_one({"id": category_id})
    return Category(**parse_from_mongo(updated_category))

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, current_user: UserResponse = Depends(get_current_partner)):
    # Check if category is in use by any tasks
    tasks_using_category = await db.tasks.count_documents({"category": category_id})
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
    clients = await db.clients.find({"active": True}).sort("name", 1).to_list(length=5000)
    return [Client(**parse_from_mongo(client)) for client in clients]

@api_router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str, current_user: UserResponse = Depends(get_current_user)):
    client = await db.clients.find_one({"id": client_id, "active": True})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return Client(**parse_from_mongo(client))

@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(
    client_id: str, 
    client_update: ClientUpdate, 
    current_user: UserResponse = Depends(get_current_partner)
):
    existing_client = await db.clients.find_one({"id": client_id, "active": True})
    if not existing_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = {k: v for k, v in client_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Check if name is being changed and if it already exists
    if "name" in update_data and update_data["name"] != existing_client["name"]:
        existing_name = await db.clients.find_one({"name": update_data["name"], "active": True})
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
    # Build query based on user role
    task_query = {}
    if current_user.role != UserRole.PARTNER:
        task_query["assignee_id"] = current_user.id
    
    # Update overdue tasks before getting counts
    await update_overdue_tasks()
    
    # Get counts by status
    pending_count = await db.tasks.count_documents({**task_query, "status": TaskStatus.PENDING})
    on_hold_count = await db.tasks.count_documents({**task_query, "status": TaskStatus.ON_HOLD})
    completed_count = await db.tasks.count_documents({**task_query, "status": TaskStatus.COMPLETED})
    overdue_count = await db.tasks.count_documents({**task_query, "status": TaskStatus.OVERDUE})
    
    # Get overdue tasks (all for partners, own for others)
    overdue_tasks = await db.tasks.find({**task_query, "status": TaskStatus.OVERDUE}).sort("due_date", 1).to_list(length=5000)
    
    # Get tasks due in next 7 days (pending/overdue with due date within 7 days)
    today = datetime.now(timezone.utc)
    seven_days_later = today + timedelta(days=7)
    
    due_7_days_query = {
        **task_query,
        "status": {"$in": [TaskStatus.PENDING, TaskStatus.OVERDUE]},
        "due_date": {"$lte": seven_days_later.isoformat(), "$gte": today.strftime("%Y-%m-%d")}
    }
    due_7_days_tasks = await db.tasks.find(due_7_days_query).sort("due_date", 1).to_list(length=5000)
    
    # For backward compatibility, also include recent_tasks
    recent_tasks = overdue_tasks + due_7_days_tasks
    
    # Get team performance (only for partners)
    team_stats = []
    if current_user.role == UserRole.PARTNER:
        users = await db.users.find({"active": True}).to_list(length=5000)
        
        for user in users:
            user_tasks = await db.tasks.count_documents({"assignee_id": user["id"]})
            completed_tasks = await db.tasks.count_documents({"assignee_id": user["id"], "status": TaskStatus.COMPLETED})
            
            team_stats.append({
                "user_id": user["id"],
                "name": user["name"],
                "role": user["role"],
                "total_tasks": user_tasks,
                "completed_tasks": completed_tasks,
                "completion_rate": (completed_tasks / user_tasks * 100) if user_tasks > 0 else 0
            })
    
    # Get client analytics (only for partners)
    client_stats = []
    if current_user.role == UserRole.PARTNER:
        clients = await db.tasks.distinct("client_name")
        for client in clients[:5]:  # Top 5 clients
            if client:
                client_tasks = await db.tasks.count_documents({"client_name": client})
                completed_client_tasks = await db.tasks.count_documents({"client_name": client, "status": TaskStatus.COMPLETED})
                client_stats.append({
                    "client_name": client,
                    "total_tasks": client_tasks,
                    "completed_tasks": completed_client_tasks,
                    "completion_rate": (completed_client_tasks / client_tasks * 100) if client_tasks > 0 else 0
                })
    
    # Get category analytics (only for partners)
    category_stats = []
    if current_user.role == UserRole.PARTNER:
        categories = await db.tasks.distinct("category")
        for category in categories:
            if category:
                category_tasks = await db.tasks.count_documents({"category": category})
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

# ==================== ATTENDANCE ENDPOINTS ====================

@api_router.get("/attendance/settings")
async def get_attendance_settings(current_user: UserResponse = Depends(get_current_user)):
    """Get geofence settings"""
    settings = await get_geofence_settings()
    return settings

@api_router.put("/attendance/settings")
async def update_attendance_settings(
    settings_update: GeofenceSettingsUpdate,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Update geofence settings (Partners only)"""
    update_data = {k: v for k, v in settings_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_data["updated_by"] = current_user.name
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # If locations are updated, reverse geocode addresses for any without addresses
    if "locations" in update_data:
        locations = update_data["locations"]
        if len(locations) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 locations allowed")
        for loc in locations:
            if loc.get("latitude") and loc.get("longitude") and not loc.get("address"):
                address = await reverse_geocode(loc["latitude"], loc["longitude"])
                if address:
                    loc["address"] = address
    
    result = await db.geofence_settings.update_one(
        {"id": "geofence_settings"},
        {"$set": update_data},
        upsert=True
    )
    
    settings = await get_geofence_settings()
    return settings

# Attendance Rules endpoints
@api_router.get("/attendance/rules")
async def get_attendance_rules(current_user: UserResponse = Depends(get_current_user)):
    """Get attendance rules"""
    rules = await db.attendance_rules.find_one({"id": "attendance_rules"})
    if not rules:
        # Return defaults
        return {
            "id": "attendance_rules",
            "min_hours_full_day": 8.0,
            "working_days": [0, 1, 2, 3, 4, 5],  # Mon-Sat
            "working_days_names": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        }
    rules = parse_from_mongo(rules)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    rules["working_days_names"] = [day_names[d] for d in rules.get("working_days", [])]
    return rules

@api_router.put("/attendance/rules")
async def update_attendance_rules(
    rules_update: AttendanceRulesUpdate,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Update attendance rules (Partners only)"""
    update_data = {k: v for k, v in rules_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_data["updated_by"] = current_user.name
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.attendance_rules.update_one(
        {"id": "attendance_rules"},
        {"$set": update_data},
        upsert=True
    )
    
    return await get_attendance_rules(current_user)

# Holiday management endpoints
@api_router.get("/attendance/holidays")
async def get_holidays(
    year: Optional[int] = None,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get holidays for a year"""
    query = {}
    if year:
        query["date"] = {"$regex": f"^{year}"}
    
    holidays = await db.holidays.find(query).sort("date", 1).to_list(length=5000)
    return [parse_from_mongo(h) for h in holidays]

@api_router.post("/attendance/holidays")
async def add_holiday(
    holiday: HolidayCreate,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Add a holiday (Partners only)"""
    # Check if holiday already exists for this date
    existing = await db.holidays.find_one({"date": holiday.date})
    if existing:
        raise HTTPException(status_code=400, detail="Holiday already exists for this date")
    
    holiday_dict = {
        "id": str(uuid.uuid4()),
        "date": holiday.date,
        "name": holiday.name,
        "is_paid": holiday.is_paid,
        "created_by": current_user.name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.holidays.insert_one(holiday_dict)
    return parse_from_mongo(holiday_dict)

@api_router.delete("/attendance/holidays/{holiday_id}")
async def delete_holiday(
    holiday_id: str,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Delete a holiday (Partners only)"""
    result = await db.holidays.delete_one({"id": holiday_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Holiday not found")
    return {"message": "Holiday deleted successfully"}

@api_router.post("/attendance/clock-in")
async def clock_in(
    attendance_data: AttendanceCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Clock in with GPS location"""
    # Check if already clocked in today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    existing_clock_in = await db.attendance.find_one({
        "user_id": current_user.id,
        "type": AttendanceType.CLOCK_IN.value,
        "timestamp": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    if existing_clock_in:
        raise HTTPException(status_code=400, detail="Already clocked in today")
    
    now_utc = datetime.now(timezone.utc)
    
    # Get geofence settings
    settings = await get_geofence_settings()
    
    # Calculate distance from office locations if geofence is configured
    is_within_geofence = None
    distance_from_office = None
    nearest_location = None
    gps_accuracy = attendance_data.accuracy or 0
    
    locations = settings.get("locations", [])
    if settings.get("enabled") and locations:
        is_within_geofence, distance_from_office, nearest_location = check_within_any_geofence(
            attendance_data.latitude, attendance_data.longitude,
            locations, settings.get("radius_meters", 100),
            gps_accuracy
        )
        
        if not is_within_geofence:
            # Calculate effective radius for error message
            tolerance = min(gps_accuracy, 50) if gps_accuracy else 0
            effective_radius = settings.get('radius_meters', 100) + tolerance
            accuracy_note = f" (GPS accuracy: ±{gps_accuracy:.0f}m)" if gps_accuracy else ""
            raise HTTPException(
                status_code=400, 
                detail=f"You are {distance_from_office:.0f}m away from the nearest office ({nearest_location}). Must be within {effective_radius:.0f}m to clock in.{accuracy_note}"
            )
    
    # Reverse geocode the address
    address = await reverse_geocode(attendance_data.latitude, attendance_data.longitude)
    
    attendance_dict = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "user_name": current_user.name,
        "type": AttendanceType.CLOCK_IN.value,
        "timestamp": now_utc.isoformat(),
        "timestamp_ist": format_ist_datetime(now_utc),
        "latitude": attendance_data.latitude,
        "longitude": attendance_data.longitude,
        "accuracy": gps_accuracy,
        "address": address,
        "is_within_geofence": is_within_geofence,
        "distance_from_office": distance_from_office,
        "nearest_location": nearest_location,
        "device_info": attendance_data.device_info
    }
    
    attendance_dict = prepare_for_mongo(attendance_dict)
    await db.attendance.insert_one(attendance_dict)
    
    # Create notification for successful clock-in
    await create_notification(
        user_id=current_user.id,
        title="Clocked In",
        message=f"You clocked in at {format_ist_datetime(now_utc)}"
    )
    
    return {
        "message": "Clocked in successfully",
        "attendance": parse_from_mongo(attendance_dict),
        "address": address
    }

@api_router.post("/attendance/clock-out")
async def clock_out(
    attendance_data: AttendanceCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Clock out with GPS location"""
    # Check if clocked in today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    existing_clock_in = await db.attendance.find_one({
        "user_id": current_user.id,
        "type": AttendanceType.CLOCK_IN.value,
        "timestamp": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    if not existing_clock_in:
        raise HTTPException(status_code=400, detail="You haven't clocked in today")
    
    # Check if already clocked out
    existing_clock_out = await db.attendance.find_one({
        "user_id": current_user.id,
        "type": AttendanceType.CLOCK_OUT.value,
        "timestamp": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    if existing_clock_out:
        raise HTTPException(status_code=400, detail="Already clocked out today")
    
    now_utc = datetime.now(timezone.utc)
    
    # Get geofence settings
    settings = await get_geofence_settings()
    
    # Calculate distance from office (for record, not enforced on clock out)
    is_within_geofence = None
    distance_from_office = None
    nearest_location = None
    gps_accuracy = attendance_data.accuracy or 0
    
    locations = settings.get("locations", [])
    if locations:
        is_within_geofence, distance_from_office, nearest_location = check_within_any_geofence(
            attendance_data.latitude, attendance_data.longitude,
            locations, settings.get("radius_meters", 100),
            gps_accuracy
        )
    
    # Reverse geocode the address
    address = await reverse_geocode(attendance_data.latitude, attendance_data.longitude)
    
    attendance_dict = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "user_name": current_user.name,
        "type": AttendanceType.CLOCK_OUT.value,
        "timestamp": now_utc.isoformat(),
        "timestamp_ist": format_ist_datetime(now_utc),
        "latitude": attendance_data.latitude,
        "longitude": attendance_data.longitude,
        "accuracy": gps_accuracy,
        "address": address,
        "is_within_geofence": is_within_geofence,
        "distance_from_office": distance_from_office,
        "nearest_location": nearest_location,
        "device_info": attendance_data.device_info
    }
    
    attendance_dict = prepare_for_mongo(attendance_dict)
    await db.attendance.insert_one(attendance_dict)
    
    # Calculate work duration
    clock_in_time = datetime.fromisoformat(existing_clock_in["timestamp"])
    work_duration = now_utc - clock_in_time
    hours = work_duration.total_seconds() / 3600
    
    # Create notification
    await create_notification(
        user_id=current_user.id,
        title="Clocked Out",
        message=f"You clocked out at {format_ist_datetime(now_utc)}. Work duration: {round(hours, 2)} hours"
    )
    
    return {
        "message": "Clocked out successfully",
        "attendance": parse_from_mongo(attendance_dict),
        "address": address,
        "work_duration_hours": round(hours, 2)
    }

@api_router.get("/attendance/today")
async def get_today_attendance(current_user: UserResponse = Depends(get_current_user)):
    """Get today's attendance status for current user"""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    records = await db.attendance.find({
        "user_id": current_user.id,
        "timestamp": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    }).sort("timestamp", 1).to_list(length=5000)
    
    clock_in = None
    clock_out = None
    
    for record in records:
        parsed_record = parse_from_mongo(record)
        if parsed_record["type"] == AttendanceType.CLOCK_IN:
            clock_in = parsed_record
        elif parsed_record["type"] == AttendanceType.CLOCK_OUT:
            clock_out = parsed_record
    
    work_duration = None
    if clock_in and clock_out:
        in_time = clock_in["timestamp"] if isinstance(clock_in["timestamp"], datetime) else datetime.fromisoformat(clock_in["timestamp"])
        out_time = clock_out["timestamp"] if isinstance(clock_out["timestamp"], datetime) else datetime.fromisoformat(clock_out["timestamp"])
        work_duration = round((out_time - in_time).total_seconds() / 3600, 2)
    
    return {
        "clock_in": clock_in,
        "clock_out": clock_out,
        "is_clocked_in": clock_in is not None and clock_out is None,
        "work_duration_hours": work_duration
    }

@api_router.get("/attendance/history")
async def get_attendance_history(
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get attendance history. Partners can view all users, others only their own."""
    query = {}
    
    # Non-partners can only view their own attendance
    if current_user.role != UserRole.PARTNER:
        query["user_id"] = current_user.id
    elif user_id:
        query["user_id"] = user_id
    
    # Date filtering
    if start_date:
        query.setdefault("timestamp", {})["$gte"] = start_date
    if end_date:
        query.setdefault("timestamp", {})["$lte"] = end_date
    
    records = await db.attendance.find(query).sort("timestamp", -1).to_list(length=500)
    
    return [parse_from_mongo(record) for record in records]

@api_router.delete("/attendance/{attendance_id}")
async def delete_attendance_record(
    attendance_id: str,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Delete an attendance record (Partners only)"""
    # Find the attendance record
    record = await db.attendance.find_one({"id": attendance_id})
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Delete the record
    result = await db.attendance.delete_one({"id": attendance_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Create notification for the user whose attendance was deleted
    await create_notification(
        user_id=record["user_id"],
        title="Attendance Record Deleted",
        message=f"Your {record['type']} record for {record.get('timestamp_ist', 'N/A')} has been deleted by {current_user.name}"
    )
    
    return {"message": "Attendance record deleted successfully"}

@api_router.get("/attendance/report")
async def get_attendance_report(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Get monthly attendance report for all users (Partners only)"""
    now = datetime.now(timezone.utc)
    report_month = month or now.month
    report_year = year or now.year
    
    # Calculate date range
    start_date = datetime(report_year, report_month, 1, tzinfo=timezone.utc)
    if report_month == 12:
        end_date = datetime(report_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(report_year, report_month + 1, 1, tzinfo=timezone.utc)
    
    # Get attendance rules
    rules = await db.attendance_rules.find_one({"id": "attendance_rules"})
    min_hours_full_day = rules.get("min_hours_full_day", 8.0) if rules else 8.0
    working_days = rules.get("working_days", [0, 1, 2, 3, 4, 5]) if rules else [0, 1, 2, 3, 4, 5]  # Mon-Sat
    
    # Get holidays for the month
    holidays = await db.holidays.find({
        "date": {"$regex": f"^{report_year}-{report_month:02d}"}
    }).to_list(length=5000)
    holiday_dates = {h["date"] for h in holidays}
    
    # Calculate working days in the month (excluding Sundays and holidays)
    total_working_days = 0
    total_sundays = 0
    total_holidays = 0
    current_date = start_date
    while current_date < end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        weekday = current_date.weekday()  # 0=Monday, 6=Sunday
        
        if weekday == 6:  # Sunday
            total_sundays += 1
        elif date_str in holiday_dates:
            total_holidays += 1
        elif weekday in working_days:
            total_working_days += 1
        
        current_date += timedelta(days=1)
    
    # Get all users
    users = await db.users.find({"active": True}).to_list(length=5000)
    
    report = []
    for user in users:
        # Get attendance records for this user in the month
        records = await db.attendance.find({
            "user_id": user["id"],
            "timestamp": {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}
        }).to_list(length=5000)
        
        # Group by date
        clock_ins = [r for r in records if r["type"] == AttendanceType.CLOCK_IN.value]
        clock_outs = [r for r in records if r["type"] == AttendanceType.CLOCK_OUT.value]
        
        full_days = 0
        half_days = 0
        total_hours = 0
        daily_details = []
        
        for cin in clock_ins:
            cin_date = datetime.fromisoformat(cin["timestamp"]).date()
            date_str = cin_date.strftime("%Y-%m-%d")
            
            matching_out = next(
                (co for co in clock_outs 
                 if datetime.fromisoformat(co["timestamp"]).date() == cin_date),
                None
            )
            
            if matching_out:
                in_time = datetime.fromisoformat(cin["timestamp"])
                out_time = datetime.fromisoformat(matching_out["timestamp"])
                hours = (out_time - in_time).total_seconds() / 3600
                total_hours += hours
                
                # Determine if full day or half day
                if hours >= min_hours_full_day:
                    full_days += 1
                    day_type = "full"
                else:
                    half_days += 1
                    day_type = "half"
                
                daily_details.append({
                    "date": date_str,
                    "hours": round(hours, 2),
                    "type": day_type
                })
            else:
                # Clock in without clock out - mark as incomplete
                daily_details.append({
                    "date": date_str,
                    "hours": 0,
                    "type": "incomplete"
                })
        
        # Calculate absent days (working days - present days)
        present_dates = {d["date"] for d in daily_details}
        absent_days = 0
        current_date = start_date
        while current_date < end_date and current_date.date() <= now.date():
            date_str = current_date.strftime("%Y-%m-%d")
            weekday = current_date.weekday()
            
            # Skip Sundays and holidays
            if weekday != 6 and date_str not in holiday_dates and weekday in working_days:
                if date_str not in present_dates:
                    absent_days += 1
            
            current_date += timedelta(days=1)
        
        # Calculate effective days (full days + half days * 0.5)
        effective_days = full_days + (half_days * 0.5)
        
        report.append({
            "user_id": user["id"],
            "user_name": user["name"],
            "role": user["role"],
            "department": user.get("department", ""),
            "full_days": full_days,
            "half_days": half_days,
            "effective_days": effective_days,
            "absent_days": absent_days,
            "total_hours": round(total_hours, 2),
            "average_hours_per_day": round(total_hours / (full_days + half_days), 2) if (full_days + half_days) > 0 else 0
        })
    
    return {
        "month": report_month,
        "year": report_year,
        "summary": {
            "total_working_days": total_working_days,
            "total_sundays": total_sundays,
            "total_holidays": total_holidays,
            "min_hours_full_day": min_hours_full_day,
            "holidays": [{"date": h["date"], "name": h["name"]} for h in holidays]
        },
        "report": sorted(report, key=lambda x: x["user_name"])
    }

@api_router.get("/attendance/report/export")
async def export_attendance_report(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Export monthly attendance report as Excel file (Partners only)"""
    now = datetime.now(timezone.utc)
    report_month = month or now.month
    report_year = year or now.year
    
    # Calculate date range
    start_date = datetime(report_year, report_month, 1, tzinfo=timezone.utc)
    if report_month == 12:
        end_date = datetime(report_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(report_year, report_month + 1, 1, tzinfo=timezone.utc)
    
    # Get attendance rules
    rules = await db.attendance_rules.find_one({"id": "attendance_rules"})
    min_hours_full_day = rules.get("min_hours_full_day", 8.0) if rules else 8.0
    working_days = rules.get("working_days", [0, 1, 2, 3, 4, 5]) if rules else [0, 1, 2, 3, 4, 5]
    
    # Get holidays for the month
    holidays = await db.holidays.find({
        "date": {"$regex": f"^{report_year}-{report_month:02d}"}
    }).to_list(length=5000)
    holiday_dates = {h["date"] for h in holidays}
    
    # Calculate working days summary
    total_working_days = 0
    total_sundays = 0
    total_holidays = 0
    current_date = start_date
    while current_date < end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        weekday = current_date.weekday()
        
        if weekday == 6:
            total_sundays += 1
        elif date_str in holiday_dates:
            total_holidays += 1
        elif weekday in working_days:
            total_working_days += 1
        
        current_date += timedelta(days=1)
    
    # Get all users
    users = await db.users.find({"active": True}).to_list(length=5000)
    
    report_data = []
    for user in users:
        # Get attendance records for this user in the month
        records = await db.attendance.find({
            "user_id": user["id"],
            "timestamp": {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}
        }).to_list(length=5000)
        
        clock_ins = [r for r in records if r["type"] == AttendanceType.CLOCK_IN.value]
        clock_outs = [r for r in records if r["type"] == AttendanceType.CLOCK_OUT.value]
        
        full_days = 0
        half_days = 0
        total_hours = 0
        
        for cin in clock_ins:
            cin_date = datetime.fromisoformat(cin["timestamp"]).date()
            matching_out = next(
                (co for co in clock_outs 
                 if datetime.fromisoformat(co["timestamp"]).date() == cin_date),
                None
            )
            
            if matching_out:
                in_time = datetime.fromisoformat(cin["timestamp"])
                out_time = datetime.fromisoformat(matching_out["timestamp"])
                hours = (out_time - in_time).total_seconds() / 3600
                total_hours += hours
                
                if hours >= min_hours_full_day:
                    full_days += 1
                else:
                    half_days += 1
        
        # Calculate absent days
        present_dates = {datetime.fromisoformat(cin["timestamp"]).strftime("%Y-%m-%d") for cin in clock_ins}
        absent_days = 0
        current_date = start_date
        while current_date < end_date and current_date.date() <= now.date():
            date_str = current_date.strftime("%Y-%m-%d")
            weekday = current_date.weekday()
            
            if weekday != 6 and date_str not in holiday_dates and weekday in working_days:
                if date_str not in present_dates:
                    absent_days += 1
            
            current_date += timedelta(days=1)
        
        effective_days = full_days + (half_days * 0.5)
        
        report_data.append({
            "Name": user["name"],
            "Department": user.get("department", ""),
            "Role": user["role"],
            "Full Days": full_days,
            "Half Days": half_days,
            "Effective Days": effective_days,
            "Absent Days": absent_days,
            "Total Hours": round(total_hours, 2),
            "Avg Hours/Day": round(total_hours / (full_days + half_days), 2) if (full_days + half_days) > 0 else 0
        })
    
    # Create daily detail data (employee-wise in/out times)
    daily_detail_data = []
    for user in users:
        # Get attendance records for this user in the month
        records = await db.attendance.find({
            "user_id": user["id"],
            "timestamp": {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}
        }).to_list(length=5000)
        
        clock_ins = {datetime.fromisoformat(r["timestamp"]).strftime("%Y-%m-%d"): r 
                     for r in records if r["type"] == AttendanceType.CLOCK_IN.value}
        clock_outs = {datetime.fromisoformat(r["timestamp"]).strftime("%Y-%m-%d"): r 
                      for r in records if r["type"] == AttendanceType.CLOCK_OUT.value}
        
        # Iterate through each day of the month
        current_date = start_date
        while current_date < end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            weekday = current_date.weekday()
            day_name = current_date.strftime("%A")
            
            cin = clock_ins.get(date_str)
            cout = clock_outs.get(date_str)
            
            in_time_str = ""
            out_time_str = ""
            hours_worked = ""
            day_type = ""
            status = ""
            clock_in_location = ""
            clock_out_location = ""
            
            # Determine status
            if weekday == 6:
                status = "Weekly Off"
            elif date_str in holiday_dates:
                holiday_name = next((h["name"] for h in holidays if h["date"] == date_str), "Holiday")
                status = f"Holiday ({holiday_name})"
            elif weekday not in working_days:
                status = "Weekly Off"
            elif cin:
                # Convert to IST for display
                in_time = datetime.fromisoformat(cin["timestamp"])
                in_time_ist = in_time + timedelta(hours=5, minutes=30)
                in_time_str = in_time_ist.strftime("%I:%M %p")
                
                # Get clock-in location
                clock_in_location = cin.get("address", "")
                
                if cout:
                    out_time = datetime.fromisoformat(cout["timestamp"])
                    out_time_ist = out_time + timedelta(hours=5, minutes=30)
                    out_time_str = out_time_ist.strftime("%I:%M %p")
                    
                    # Get clock-out location
                    clock_out_location = cout.get("address", "")
                    
                    hours = (out_time - in_time).total_seconds() / 3600
                    hours_worked = f"{hours:.2f}"
                    day_type = "Full Day" if hours >= min_hours_full_day else "Half Day"
                    status = "Present"
                else:
                    status = "Clocked In (No Clock Out)"
            elif current_date.date() <= now.date():
                status = "Absent"
            else:
                status = "-"  # Future date
            
            daily_detail_data.append({
                "Date": date_str,
                "Day": day_name,
                "Employee": user["name"],
                "Department": user.get("department", ""),
                "Clock In": in_time_str,
                "Clock In Location": clock_in_location,
                "Clock Out": out_time_str,
                "Clock Out Location": clock_out_location,
                "Hours Worked": hours_worked,
                "Day Type": day_type,
                "Status": status
            })
            
            current_date += timedelta(days=1)
    
    # Create summary data
    month_names = ["January", "February", "March", "April", "May", "June", 
                   "July", "August", "September", "October", "November", "December"]
    
    summary_data = [
        {"Summary": "Month", "Value": f"{month_names[report_month-1]} {report_year}"},
        {"Summary": "Working Days", "Value": total_working_days},
        {"Summary": "Weekly Offs (Sundays)", "Value": total_sundays},
        {"Summary": "Holidays", "Value": total_holidays},
        {"Summary": "Min Hours for Full Day", "Value": min_hours_full_day},
    ]
    
    # Add holiday list
    for i, h in enumerate(holidays):
        summary_data.append({"Summary": f"Holiday {i+1}", "Value": f"{h['date']}: {h['name']}"})
    
    # Create Excel file with multiple sheets
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # Report sheet (employee-wise monthly summary)
        df_report = pd.DataFrame(sorted(report_data, key=lambda x: x["Name"]))
        df_report.to_excel(writer, sheet_name='Monthly Summary', index=False)
        
        # Daily detail sheet (employee-wise daily in/out times)
        df_daily = pd.DataFrame(daily_detail_data)
        # Sort by date then by employee name
        df_daily = df_daily.sort_values(by=['Date', 'Employee'])
        df_daily.to_excel(writer, sheet_name='Daily Details', index=False)
        
        # Adjust column widths for Daily Details sheet
        worksheet = writer.sheets['Daily Details']
        column_widths = {
            'A': 12,  # Date
            'B': 12,  # Day
            'C': 20,  # Employee
            'D': 15,  # Department
            'E': 12,  # Clock In
            'F': 40,  # Clock In Location
            'G': 12,  # Clock Out
            'H': 40,  # Clock Out Location
            'I': 14,  # Hours Worked
            'J': 12,  # Day Type
            'K': 25,  # Status
        }
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width
    
    output.seek(0)
    
    filename = f"Attendance_Report_{month_names[report_month-1]}_{report_year}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==================== TIMESHEET ENDPOINTS ====================

@api_router.get("/timesheet")
async def get_timesheet(
    period: str = "weekly",  # daily, weekly, monthly
    user_id: Optional[str] = None,
    date: Optional[str] = None,  # YYYY-MM-DD for reference date
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get timesheet data for a user
    - period: daily, weekly, monthly
    - user_id: Optional, partners can view any user's timesheet
    - date: Reference date (defaults to today)
    """
    # Determine which user's timesheet to fetch
    target_user_id = user_id if user_id and current_user.role == UserRole.PARTNER else current_user.id
    
    # Parse reference date
    if date:
        try:
            ref_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        ref_date = datetime.now(timezone.utc)
    
    # Calculate date range based on period
    if period == "daily":
        start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        period_label = ref_date.strftime("%d %b %Y")
    elif period == "weekly":
        # Start from Monday
        days_since_monday = ref_date.weekday()
        start_date = (ref_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        period_label = f"{start_date.strftime('%d %b')} - {(end_date - timedelta(days=1)).strftime('%d %b %Y')}"
    elif period == "monthly":
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ref_date.month == 12:
            end_date = start_date.replace(year=ref_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=ref_date.month + 1)
        period_label = ref_date.strftime("%B %Y")
    else:
        raise HTTPException(status_code=400, detail="Invalid period. Use daily, weekly, or monthly")
    
    # Get completed tasks in the date range for the user
    completed_tasks = await db.tasks.find({
        "assignee_id": target_user_id,
        "status": TaskStatus.COMPLETED,
        "completed_at": {
            "$gte": start_date.isoformat(),
            "$lt": end_date.isoformat()
        }
    }).sort("completed_at", 1).to_list(length=500)
    
    # Get user info
    user = await db.users.find_one({"id": target_user_id})
    user_name = user["name"] if user else "Unknown"
    
    # Build timesheet entries
    entries = []
    total_hours = 0
    
    for task in completed_tasks:
        actual_hours = task.get("actual_hours", 0) or 0
        total_hours += actual_hours
        
        completed_at = task.get("completed_at")
        if completed_at:
            completed_dt = datetime.fromisoformat(completed_at)
            completed_ist = completed_dt + timedelta(hours=5, minutes=30)
            completed_date = completed_ist.strftime("%Y-%m-%d")
            completed_time = completed_ist.strftime("%I:%M %p")
        else:
            completed_date = "N/A"
            completed_time = "N/A"
        
        entries.append({
            "task_id": task["id"],
            "title": task["title"],
            "client_name": task.get("client_name", ""),
            "category": task.get("category", ""),
            "completed_date": completed_date,
            "completed_time": completed_time,
            "estimated_hours": task.get("estimated_hours"),
            "actual_hours": actual_hours,
            "description": task.get("description", "")
        })
    
    # Group by date for summary
    daily_summary = {}
    for entry in entries:
        date_key = entry["completed_date"]
        if date_key not in daily_summary:
            daily_summary[date_key] = {"tasks": 0, "hours": 0}
        daily_summary[date_key]["tasks"] += 1
        daily_summary[date_key]["hours"] += entry["actual_hours"]
    
    return {
        "user_id": target_user_id,
        "user_name": user_name,
        "period": period,
        "period_label": period_label,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": (end_date - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_tasks": len(entries),
        "total_hours": round(total_hours, 2),
        "daily_summary": daily_summary,
        "entries": entries
    }

@api_router.get("/timesheet/team")
async def get_team_timesheet(
    period: str = "weekly",
    date: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Get timesheet summary for all team members (Partners only)"""
    # Parse reference date
    if date:
        try:
            ref_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        ref_date = datetime.now(timezone.utc)
    
    # Calculate date range
    if period == "daily":
        start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        period_label = ref_date.strftime("%d %b %Y")
    elif period == "weekly":
        days_since_monday = ref_date.weekday()
        start_date = (ref_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        period_label = f"{start_date.strftime('%d %b')} - {(end_date - timedelta(days=1)).strftime('%d %b %Y')}"
    elif period == "monthly":
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ref_date.month == 12:
            end_date = start_date.replace(year=ref_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=ref_date.month + 1)
        period_label = ref_date.strftime("%B %Y")
    else:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    # Get all active users
    users = await db.users.find({"active": True}).to_list(length=100)
    
    team_summary = []
    grand_total_hours = 0
    grand_total_tasks = 0
    
    for user in users:
        # Get completed tasks for this user
        completed_tasks = await db.tasks.find({
            "assignee_id": user["id"],
            "status": TaskStatus.COMPLETED,
            "completed_at": {
                "$gte": start_date.isoformat(),
                "$lt": end_date.isoformat()
            }
        }).to_list(length=500)
        
        total_hours = sum(t.get("actual_hours", 0) or 0 for t in completed_tasks)
        task_count = len(completed_tasks)
        
        grand_total_hours += total_hours
        grand_total_tasks += task_count
        
        team_summary.append({
            "user_id": user["id"],
            "user_name": user["name"],
            "department": user.get("department", ""),
            "role": user["role"],
            "tasks_completed": task_count,
            "total_hours": round(total_hours, 2),
            "avg_hours_per_task": round(total_hours / task_count, 2) if task_count > 0 else 0
        })
    
    # Sort by total hours descending
    team_summary.sort(key=lambda x: x["total_hours"], reverse=True)
    
    return {
        "period": period,
        "period_label": period_label,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": (end_date - timedelta(days=1)).strftime("%Y-%m-%d"),
        "grand_total_tasks": grand_total_tasks,
        "grand_total_hours": round(grand_total_hours, 2),
        "team_summary": team_summary
    }

@api_router.get("/timesheet/export")
async def export_timesheet(
    period: str = "weekly",
    user_id: Optional[str] = None,
    date: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user)
):
    """Export timesheet as Excel file"""
    # Get timesheet data
    target_user_id = user_id if user_id and current_user.role == UserRole.PARTNER else current_user.id
    
    # Parse reference date
    if date:
        try:
            ref_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        ref_date = datetime.now(timezone.utc)
    
    # Calculate date range
    if period == "daily":
        start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        period_label = ref_date.strftime("%d_%b_%Y")
    elif period == "weekly":
        days_since_monday = ref_date.weekday()
        start_date = (ref_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        period_label = f"{start_date.strftime('%d%b')}_to_{(end_date - timedelta(days=1)).strftime('%d%b_%Y')}"
    else:  # monthly
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ref_date.month == 12:
            end_date = start_date.replace(year=ref_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=ref_date.month + 1)
        period_label = ref_date.strftime("%B_%Y")
    
    # Get user info
    user = await db.users.find_one({"id": target_user_id})
    user_name = user["name"] if user else "Unknown"
    
    # Get completed tasks
    completed_tasks = await db.tasks.find({
        "assignee_id": target_user_id,
        "status": TaskStatus.COMPLETED,
        "completed_at": {
            "$gte": start_date.isoformat(),
            "$lt": end_date.isoformat()
        }
    }).sort("completed_at", 1).to_list(length=500)
    
    # Build data for Excel
    timesheet_data = []
    total_hours = 0
    
    for task in completed_tasks:
        actual_hours = task.get("actual_hours", 0) or 0
        total_hours += actual_hours
        
        completed_at = task.get("completed_at")
        if completed_at:
            completed_dt = datetime.fromisoformat(completed_at)
            completed_ist = completed_dt + timedelta(hours=5, minutes=30)
            completed_date = completed_ist.strftime("%d-%b-%Y")
            day_name = completed_ist.strftime("%A")
        else:
            completed_date = "N/A"
            day_name = ""
        
        timesheet_data.append({
            "Date": completed_date,
            "Day": day_name,
            "Task": task["title"],
            "Client": task.get("client_name", ""),
            "Category": task.get("category", ""),
            "Description": task.get("description", "")[:100] if task.get("description") else "",
            "Est. Hours": task.get("estimated_hours", ""),
            "Actual Hours": actual_hours
        })
    
    # Create summary data
    summary_data = [
        {"Field": "Employee", "Value": user_name},
        {"Field": "Period", "Value": period.capitalize()},
        {"Field": "Date Range", "Value": f"{start_date.strftime('%d %b %Y')} - {(end_date - timedelta(days=1)).strftime('%d %b %Y')}"},
        {"Field": "Total Tasks", "Value": len(completed_tasks)},
        {"Field": "Total Hours", "Value": round(total_hours, 2)},
        {"Field": "Avg Hours/Task", "Value": round(total_hours / len(completed_tasks), 2) if completed_tasks else 0}
    ]
    
    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # Timesheet details
        if timesheet_data:
            df_timesheet = pd.DataFrame(timesheet_data)
            df_timesheet.to_excel(writer, sheet_name='Timesheet', index=False)
            
            # Adjust column widths
            worksheet = writer.sheets['Timesheet']
            column_widths = {'A': 12, 'B': 12, 'C': 30, 'D': 20, 'E': 15, 'F': 40, 'G': 12, 'H': 12}
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
    
    output.seek(0)
    
    safe_name = user_name.replace(" ", "_")
    filename = f"Timesheet_{safe_name}_{period_label}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/timesheet/team/export")
async def export_team_timesheet(
    period: str = "weekly",
    date: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Export team timesheet as Excel file (Partners only)"""
    # Parse reference date
    if date:
        try:
            ref_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        ref_date = datetime.now(timezone.utc)
    
    # Calculate date range
    if period == "daily":
        start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        period_label = ref_date.strftime("%d_%b_%Y")
    elif period == "weekly":
        days_since_monday = ref_date.weekday()
        start_date = (ref_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        period_label = f"{start_date.strftime('%d%b')}_to_{(end_date - timedelta(days=1)).strftime('%d%b_%Y')}"
    else:
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ref_date.month == 12:
            end_date = start_date.replace(year=ref_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=ref_date.month + 1)
        period_label = ref_date.strftime("%B_%Y")
    
    # Get all users
    users = await db.users.find({"active": True}).to_list(length=100)
    
    # Build team summary
    team_data = []
    all_tasks_data = []
    grand_total_hours = 0
    
    for user in users:
        completed_tasks = await db.tasks.find({
            "assignee_id": user["id"],
            "status": TaskStatus.COMPLETED,
            "completed_at": {
                "$gte": start_date.isoformat(),
                "$lt": end_date.isoformat()
            }
        }).sort("completed_at", 1).to_list(length=500)
        
        total_hours = sum(t.get("actual_hours", 0) or 0 for t in completed_tasks)
        grand_total_hours += total_hours
        
        team_data.append({
            "Employee": user["name"],
            "Department": user.get("department", ""),
            "Role": user["role"].capitalize(),
            "Tasks Completed": len(completed_tasks),
            "Total Hours": round(total_hours, 2),
            "Avg Hours/Task": round(total_hours / len(completed_tasks), 2) if completed_tasks else 0
        })
        
        # Add individual task entries
        for task in completed_tasks:
            completed_at = task.get("completed_at")
            if completed_at:
                completed_dt = datetime.fromisoformat(completed_at)
                completed_ist = completed_dt + timedelta(hours=5, minutes=30)
                completed_date = completed_ist.strftime("%d-%b-%Y")
            else:
                completed_date = "N/A"
            
            all_tasks_data.append({
                "Employee": user["name"],
                "Date": completed_date,
                "Task": task["title"],
                "Description": (task.get("description", "") or "")[:150],  # Truncate long descriptions
                "Client": task.get("client_name", ""),
                "Category": task.get("category", ""),
                "Est. Hours": task.get("estimated_hours", ""),
                "Actual Hours": task.get("actual_hours", 0)
            })
    
    # Sort team by hours
    team_data.sort(key=lambda x: x["Total Hours"], reverse=True)
    
    # Create Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary
        summary_data = [
            {"Field": "Period", "Value": period.capitalize()},
            {"Field": "Date Range", "Value": f"{start_date.strftime('%d %b %Y')} - {(end_date - timedelta(days=1)).strftime('%d %b %Y')}"},
            {"Field": "Total Team Hours", "Value": round(grand_total_hours, 2)},
            {"Field": "Total Tasks", "Value": len(all_tasks_data)}
        ]
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # Team summary
        df_team = pd.DataFrame(team_data)
        df_team.to_excel(writer, sheet_name='Team Summary', index=False)
        
        # All tasks detail
        if all_tasks_data:
            df_tasks = pd.DataFrame(all_tasks_data)
            df_tasks.to_excel(writer, sheet_name='All Tasks', index=False)
    
    output.seek(0)
    
    filename = f"Team_Timesheet_{period_label}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

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