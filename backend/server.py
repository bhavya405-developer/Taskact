from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
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
    # Status change history - records all status changes with IST timestamps
    status_history: Optional[List[dict]] = None

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    client_name: str
    category: str
    assignee_id: str
    creator_id: str
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None
    category: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None

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

def check_within_any_geofence(lat: float, lon: float, locations: list, radius: float) -> tuple:
    """Check if coordinates are within any of the geofence locations. Returns (is_within, closest_distance, closest_location_name)"""
    if not locations:
        return (None, None, None)
    
    closest_distance = float('inf')
    closest_location = None
    is_within = False
    
    for loc in locations:
        if loc.get("latitude") and loc.get("longitude"):
            distance = haversine_distance(lat, lon, loc["latitude"], loc["longitude"])
            if distance < closest_distance:
                closest_distance = distance
                closest_location = loc.get("name", "Unknown")
            if distance <= radius:
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
    
    # Get all pending and on_hold tasks with due dates
    tasks = await db.tasks.find({
        "status": {"$in": [TaskStatus.PENDING, TaskStatus.ON_HOLD]},
        "due_date": {"$ne": None}
    }).to_list(length=None)
    
    updated_count = 0
    for task in tasks:
        due_date_str = task.get('due_date')
        if due_date_str:
            try:
                # Parse the due date string to datetime object
                due_date = datetime.fromisoformat(due_date_str)
                
                # Check if task is actually overdue
                if due_date < current_time:
                    await db.tasks.update_one(
                        {"id": task["id"]},
                        {"$set": {
                            "status": TaskStatus.OVERDUE,
                            "updated_at": current_time.isoformat()
                        }}
                    )
                    updated_count += 1
            except Exception as e:
                # Log error but continue processing other tasks
                print(f"Error processing overdue task {task.get('id', 'unknown')}: {e}")
    
    return updated_count

# API Routes

# Authentication endpoints
@api_router.post("/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    user = await db.users.find_one({"email": login_data.email, "active": True})
    if not user or not verify_password(login_data.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(**parse_from_mongo(user))
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    return current_user

# Forgot Password endpoints
@api_router.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Send OTP to partner's notification for password reset"""
    # Check if user exists
    user = await db.users.find_one({"email": request.email})
    if not user:
        # Return success even if user doesn't exist (security - don't reveal user existence)
        return {"message": "Password reset request submitted. Please contact your partner for the OTP."}
    
    # Check if user is active
    if not user.get("active", True):
        return {"message": "Password reset request submitted. Please contact your partner for the OTP."}
    
    # Generate OTP
    otp = generate_otp(6)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Invalidate any existing OTPs for this email
    await db.otp_records.update_many(
        {"email": request.email, "used": False},
        {"$set": {"used": True}}
    )
    
    # Store OTP in database
    otp_record = OTPRecord(
        email=request.email,
        otp=otp,
        expires_at=expires_at
    )
    otp_dict = prepare_for_mongo(otp_record.dict())
    await db.otp_records.insert_one(otp_dict)
    
    # Send OTP to all partners' notification panel instead of email
    user_name = user.get("name", "User")
    partners = await db.users.find({"role": "partner", "active": True}).to_list(length=None)
    
    for partner in partners:
        await create_notification(
            user_id=partner["id"],
            title="Password Reset OTP Request",
            message=f"{user_name} ({request.email}) has requested a password reset. OTP: {otp} (Valid for 10 minutes)"
        )
    
    return {
        "message": "Password reset request submitted. Please contact your partner for the OTP."
    }

@api_router.post("/auth/verify-otp")
async def verify_otp(request: VerifyOTPRequest):
    """Verify OTP without resetting password (optional step for UI validation)"""
    # Find valid OTP
    otp_record = await db.otp_records.find_one({
        "email": request.email,
        "otp": request.otp,
        "used": False
    })
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Check if OTP is expired
    expires_at = datetime.fromisoformat(otp_record["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")
    
    return {"message": "OTP verified successfully", "valid": True}

@api_router.post("/auth/reset-password")
async def reset_password_with_otp(request: ResetPasswordWithOTPRequest):
    """Reset password using OTP"""
    # Find valid OTP
    otp_record = await db.otp_records.find_one({
        "email": request.email,
        "otp": request.otp,
        "used": False
    })
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Check if OTP is expired
    expires_at = datetime.fromisoformat(otp_record["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")
    
    # Find user
    user = await db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash new password
    new_password_hash = get_password_hash(request.new_password)
    
    # Update user password
    await db.users.update_one(
        {"email": request.email},
        {"$set": {"password_hash": new_password_hash}}
    )
    
    # Mark OTP as used
    await db.otp_records.update_one(
        {"id": otp_record["id"]},
        {"$set": {"used": True}}
    )
    
    # Create notification for user
    await create_notification(
        user_id=user["id"],
        title="Password Reset Successful",
        message="Your password has been successfully reset. If you did not make this change, please contact support immediately."
    )
    
    return {"message": "Password reset successful. You can now login with your new password."}

# Users endpoints
@api_router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate, current_user: UserResponse = Depends(get_current_partner)):
    # Hash the password
    password_hash = get_password_hash(user_data.password)
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_data.dict()
    user_dict.pop("password")  # Remove plain password
    user_dict["password_hash"] = password_hash
    user_dict["id"] = str(uuid.uuid4())
    user_dict["created_at"] = datetime.now(timezone.utc)
    user_dict["active"] = True
    
    user_dict = prepare_for_mongo(user_dict)
    await db.users.insert_one(user_dict)
    
    return UserResponse(**parse_from_mongo(user_dict))

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(
    current_user: UserResponse = Depends(get_current_user),
    include_inactive: bool = False
):
    """Get all users. Partners can include inactive users."""
    if include_inactive and current_user.role == UserRole.PARTNER:
        users = await db.users.find({}).to_list(length=None)
    else:
        users = await db.users.find({"active": True}).to_list(length=None)
    return [UserResponse(**parse_from_mongo(user)) for user in users]

@api_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: UserResponse = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id, "active": True})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**parse_from_mongo(user))

@api_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_profile(
    user_id: str, 
    profile_update: UserProfileUpdate, 
    current_user: UserResponse = Depends(get_current_partner)
):
    # Get existing user
    existing_user = await db.users.find_one({"id": user_id, "active": True})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prepare update data
    update_data = {k: v for k, v in profile_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Check if email is being changed and if it already exists
    if "email" in update_data and update_data["email"] != existing_user["email"]:
        existing_email = await db.users.find_one({"email": update_data["email"]})
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    # Convert datetime fields to ISO strings
    update_data = prepare_for_mongo(update_data)
    
    # Update the user
    result = await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get updated user
    updated_user = await db.users.find_one({"id": user_id})
    
    # Create notification for user about profile update
    if user_id != current_user.id:
        await create_notification(
            user_id=user_id,
            title="Profile Updated",
            message=f"Your profile has been updated by {current_user.name}",
            task_id=None
        )
    
    return UserResponse(**parse_from_mongo(updated_user))

@api_router.put("/users/{user_id}/password")
async def reset_user_password(
    user_id: str,
    password_data: PasswordResetRequest,
    current_user: UserResponse = Depends(get_current_partner)
):
    # Verify the user exists
    user = await db.users.find_one({"id": user_id, "active": True})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash the new password
    new_password_hash = get_password_hash(password_data.new_password)
    
    # Update the password
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"password_hash": new_password_hash}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create notification for user about password reset
    if user_id != current_user.id:
        await create_notification(
            user_id=user_id,
            title="Password Reset",
            message=f"Your password has been reset by {current_user.name}. Please use your new credentials to log in.",
            task_id=None
        )
    
    return {"message": "Password updated successfully"}

class ChangeOwnPasswordRequest(BaseModel):
    current_password: str
    new_password: str

@api_router.put("/auth/change-password")
async def change_own_password(
    password_data: ChangeOwnPasswordRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Allow any user to change their own password"""
    # Get user from database to verify current password
    user = await db.users.find_one({"id": current_user.id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(password_data.current_password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Hash the new password
    new_password_hash = get_password_hash(password_data.new_password)
    
    # Update the password
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"password_hash": new_password_hash}}
    )
    
    return {"message": "Password changed successfully"}

@api_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Delete a user only if they have no tasks assigned (ever)"""
    # Cannot delete yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Check if user exists
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has any tasks (current or historical)
    task_count = await db.tasks.count_documents({"assignee_id": user_id})
    if task_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete user with {task_count} task(s). Please deactivate instead to preserve task history."
        )
    
    # Delete the user permanently
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Also delete any notifications for this user
    await db.notifications.delete_many({"user_id": user_id})
    
    return {"message": f"User '{user['name']}' deleted successfully"}

@api_router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Deactivate a user - they won't be able to login but task history is preserved"""
    # Cannot deactivate yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    # Check if user exists
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already deactivated
    if not user.get("active", True):
        raise HTTPException(status_code=400, detail="User is already deactivated")
    
    # Deactivate the user
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"active": False}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User '{user['name']}' has been deactivated. They can no longer login."}

@api_router.put("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: str,
    current_user: UserResponse = Depends(get_current_partner)
):
    """Reactivate a deactivated user"""
    # Check if user exists
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already active
    if user.get("active", True):
        raise HTTPException(status_code=400, detail="User is already active")
    
    # Reactivate the user
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"active": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Notify the user
    await create_notification(
        user_id=user_id,
        title="Account Reactivated",
        message=f"Your account has been reactivated by {current_user.name}. You can now login again."
    )
    
    return {"message": f"User '{user['name']}' has been reactivated."}

# Tasks endpoints

# Task Template and Bulk Import/Export endpoints (Partners only) - Must come before parameterized routes
@api_router.get("/tasks/download-template")
async def download_tasks_template(current_user: UserResponse = Depends(get_current_partner)):
    """Download Excel template for bulk task import"""
    
    # Get active users, clients, and categories for reference
    users = await db.users.find({"active": True}).to_list(length=None)
    clients = await db.clients.find({"active": True}).to_list(length=None)
    categories = await db.categories.find({"active": True}).to_list(length=None)
    
    # Create sample data with headers
    template_data = {
        'Title': ['Review Contract for ABC Corp', 'Prepare Tax Filing', 'Client Meeting Follow-up'],
        'Description': [
            'Review and analyze the contract terms',
            'Prepare quarterly tax filing documents',
            'Follow up on action items from client meeting'
        ],
        'Client Name': [clients[0]['name'] if clients else 'Sample Client', 
                       clients[1]['name'] if len(clients) > 1 else 'Sample Client',
                       clients[0]['name'] if clients else 'Sample Client'],
        'Category': [categories[0]['name'] if categories else 'General',
                    categories[1]['name'] if len(categories) > 1 else 'General',
                    categories[0]['name'] if categories else 'General'],
        'Assignee Name': [users[1]['name'] if len(users) > 1 else users[0]['name'],
                          users[2]['name'] if len(users) > 2 else users[0]['name'],
                          users[1]['name'] if len(users) > 1 else users[0]['name']],
        'Priority': ['high', 'medium', 'low'],
        'Due Date': [
            (datetime.now(timezone.utc) + timedelta(days=7)).strftime('%d-%b-%Y'),
            (datetime.now(timezone.utc) + timedelta(days=14)).strftime('%d-%b-%Y'),
            (datetime.now(timezone.utc) + timedelta(days=3)).strftime('%d-%b-%Y')
        ]
    }
    
    df = pd.DataFrame(template_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Write data
        df.to_excel(writer, sheet_name='Tasks', index=False)
        
        # Get workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Tasks']
        
        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3B82F6',
            'font_color': 'white',
            'border': 1
        })
        
        # Format headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Set column widths
        worksheet.set_column('A:A', 35)  # Title
        worksheet.set_column('B:B', 45)  # Description
        worksheet.set_column('C:C', 25)  # Client Name
        worksheet.set_column('D:D', 20)  # Category
        worksheet.set_column('E:E', 25)  # Assignee Name
        worksheet.set_column('F:F', 12)  # Priority
        worksheet.set_column('G:G', 15)  # Due Date
        
        # Add reference sheets
        # Users reference
        users_data = {'Name': [u['name'] for u in users], 'Role': [u['role'] for u in users]}
        users_df = pd.DataFrame(users_data)
        users_df.to_excel(writer, sheet_name='Team Members (Reference)', index=False)
        
        # Clients reference
        if clients:
            clients_data = {'Client Name': [c['name'] for c in clients]}
            clients_df = pd.DataFrame(clients_data)
            clients_df.to_excel(writer, sheet_name='Clients (Reference)', index=False)
        
        # Categories reference
        if categories:
            categories_data = {'Category Name': [c['name'] for c in categories]}
            categories_df = pd.DataFrame(categories_data)
            categories_df.to_excel(writer, sheet_name='Categories (Reference)', index=False)
        
        # Add instructions sheet
        instructions_data = {
            'Instructions': [
                '1. Fill in the task information in the "Tasks" sheet',
                '2. Title: Required - Task title/name',
                '3. Description: Optional - Detailed task description',
                '4. Client Name: Required - Must match existing client name exactly',
                '5. Category: Required - Must match existing category name exactly',
                '6. Assignee Name: Required - Name of team member to assign task',
                '7. Priority: Required - Must be: low, medium, high, or urgent',
                '8. Due Date: Optional - Format: DD-MMM-YYYY (e.g., 15-Jan-2025)',
                '',
                'Reference sheets are provided for:',
                '- Team Members: List of all active users with their names',
                '- Clients: List of all active clients',
                '- Categories: List of all active categories',
                '',
                'Notes:',
                '- All tasks will be created with "pending" status',
                '- Creator will be set to the partner uploading the file',
                '- Save the file and upload it back to import tasks'
            ]
        }
        instructions_df = pd.DataFrame(instructions_data)
        instructions_df.to_excel(writer, sheet_name='Instructions', index=False)
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=tasks_template.xlsx"}
    )

@api_router.post("/tasks/bulk-import", response_model=BulkImportResult)
async def bulk_import_tasks(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_partner)
):
    """Bulk import tasks from Excel/CSV file"""
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="File must be Excel (.xlsx, .xls) or CSV (.csv)")
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse file based on extension
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(content), sheet_name='Tasks')
        
        # Validate required columns
        required_columns = ['Title', 'Client Name', 'Category', 'Assignee Name', 'Priority']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Get all users for name lookup
        users = await db.users.find({"active": True}).to_list(length=None)
        name_to_user = {u['name'].lower(): u for u in users}
        
        # Get all clients and categories for validation
        clients = await db.clients.find({"active": True}).to_list(length=None)
        client_names = {c['name'].lower(): c['name'] for c in clients}
        
        categories = await db.categories.find({"active": True}).to_list(length=None)
        category_names = {c['name'].lower(): c['name'] for c in categories}
        
        success_count = 0
        error_count = 0
        errors = []
        created_items = []
        
        # Valid priorities
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row['Title']) or str(row['Title']).strip() == '':
                    continue
                
                title = str(row['Title']).strip()
                
                # Validate and get assignee by name
                assignee_name = str(row['Assignee Name']).strip().lower()
                if assignee_name not in name_to_user:
                    errors.append(f"Row {index + 2}: Assignee name '{row['Assignee Name']}' not found")
                    error_count += 1
                    continue
                assignee = name_to_user[assignee_name]
                
                # Validate client
                client_name = str(row['Client Name']).strip()
                if client_name.lower() not in client_names:
                    errors.append(f"Row {index + 2}: Client '{client_name}' not found")
                    error_count += 1
                    continue
                actual_client_name = client_names[client_name.lower()]
                
                # Validate category
                category = str(row['Category']).strip()
                if category.lower() not in category_names:
                    errors.append(f"Row {index + 2}: Category '{category}' not found")
                    error_count += 1
                    continue
                actual_category = category_names[category.lower()]
                
                # Validate priority
                priority = str(row['Priority']).strip().lower()
                if priority not in valid_priorities:
                    errors.append(f"Row {index + 2}: Invalid priority '{row['Priority']}'. Must be: low, medium, high, or urgent")
                    error_count += 1
                    continue
                
                # Parse due date if provided (DD-MMM-YYYY format like 15-Jan-2025)
                due_date = None
                if 'Due Date' in row and pd.notna(row['Due Date']):
                    try:
                        date_str = str(row['Due Date']).strip()
                        # Try DD-MMM-YYYY format first (e.g., 15-Jan-2025)
                        try:
                            due_date = datetime.strptime(date_str, '%d-%b-%Y')
                        except ValueError:
                            # Fallback: try pandas date parsing for Excel date values
                            due_date = pd.to_datetime(row['Due Date'])
                        due_date = due_date.replace(tzinfo=timezone.utc)
                    except Exception as e:
                        errors.append(f"Row {index + 2}: Invalid date format '{row['Due Date']}'. Use DD-MMM-YYYY (e.g., 15-Jan-2025)")
                        error_count += 1
                        continue
                
                # Create task
                task_dict = {
                    "id": str(uuid.uuid4()),
                    "title": title,
                    "description": str(row.get('Description', '')).strip() if pd.notna(row.get('Description')) else None,
                    "client_name": actual_client_name,
                    "category": actual_category,
                    "assignee_id": assignee['id'],
                    "assignee_name": assignee['name'],
                    "creator_id": current_user.id,
                    "creator_name": current_user.name,
                    "status": TaskStatus.PENDING,
                    "priority": priority,
                    "due_date": due_date.isoformat() if due_date else None,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "completed_at": None
                }
                
                task_dict = prepare_for_mongo(task_dict)
                await db.tasks.insert_one(task_dict)
                
                # Create notification for assignee
                if assignee['id'] != current_user.id:
                    await create_notification(
                        user_id=assignee['id'],
                        title="New Task Assigned",
                        message=f"You have been assigned a new task: {title}",
                        task_id=task_dict['id']
                    )
                
                success_count += 1
                created_items.append(title)
                
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

@api_router.get("/tasks/export")
async def export_tasks(current_user: UserResponse = Depends(get_current_partner)):
    """Export all tasks to Excel file"""
    
    # Update overdue tasks before export
    await update_overdue_tasks()
    
    # Get all tasks
    tasks = await db.tasks.find({}).sort("created_at", -1).to_list(length=None)
    
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found to export")
    
    # Prepare data for export
    export_data = []
    for task in tasks:
        export_data.append({
            'Task ID': task['id'],
            'Title': task['title'],
            'Description': task.get('description', ''),
            'Client Name': task.get('client_name', ''),
            'Category': task.get('category', ''),
            'Assignee': task.get('assignee_name', ''),
            'Creator': task.get('creator_name', ''),
            'Status': task.get('status', ''),
            'Priority': task.get('priority', ''),
            'Due Date': task.get('due_date', '')[:10] if task.get('due_date') else '',
            'Created At': task.get('created_at', '')[:10] if task.get('created_at') else '',
            'Updated At': task.get('updated_at', '')[:10] if task.get('updated_at') else '',
            'Completed At': task.get('completed_at', '')[:10] if task.get('completed_at') else ''
        })
    
    df = pd.DataFrame(export_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='All Tasks', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['All Tasks']
        
        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#3B82F6',
            'font_color': 'white',
            'border': 1
        })
        
        # Format headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Set column widths
        worksheet.set_column('A:A', 36)  # Task ID
        worksheet.set_column('B:B', 35)  # Title
        worksheet.set_column('C:C', 45)  # Description
        worksheet.set_column('D:D', 25)  # Client Name
        worksheet.set_column('E:E', 20)  # Category
        worksheet.set_column('F:F', 20)  # Assignee
        worksheet.set_column('G:G', 20)  # Creator
        worksheet.set_column('H:H', 12)  # Status
        worksheet.set_column('I:I', 10)  # Priority
        worksheet.set_column('J:M', 12)  # Dates
        
        # Add summary sheet
        status_counts = df['Status'].value_counts().to_dict()
        priority_counts = df['Priority'].value_counts().to_dict()
        
        summary_data = {
            'Metric': ['Total Tasks', 'Pending', 'On Hold', 'Overdue', 'Completed', '', 
                      'Low Priority', 'Medium Priority', 'High Priority', 'Urgent'],
            'Count': [
                len(tasks),
                status_counts.get('pending', 0),
                status_counts.get('on_hold', 0),
                status_counts.get('overdue', 0),
                status_counts.get('completed', 0),
                '',
                priority_counts.get('low', 0),
                priority_counts.get('medium', 0),
                priority_counts.get('high', 0),
                priority_counts.get('urgent', 0)
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    output.seek(0)
    
    # Generate filename with current date
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    filename = f"tasks_export_{current_date}.xlsx"
    
    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate, current_user: UserResponse = Depends(get_current_user)):
    # Get assignee and creator names
    assignee = await db.users.find_one({"id": task_data.assignee_id})
    creator = await db.users.find_one({"id": current_user.id})  # Use current user as creator
    
    if not assignee or not creator:
        raise HTTPException(status_code=404, detail="Assignee or creator not found")
    
    # Get current IST time
    now_ist = get_ist_now()
    now_utc = datetime.now(timezone.utc)
    
    task_dict = task_data.dict()
    task_dict["creator_id"] = current_user.id  # Set current user as creator
    task_dict["assignee_name"] = assignee["name"]
    task_dict["creator_name"] = creator["name"]
    task_dict["created_at"] = now_utc
    task_dict["updated_at"] = now_utc
    
    # Initialize status history with creation entry
    task_dict["status_history"] = [{
        "status": TaskStatus.PENDING,
        "changed_at": now_utc.isoformat(),
        "changed_at_ist": format_ist_datetime(now_utc),
        "changed_by": current_user.name,
        "action": "created"
    }]
    
    task = Task(**task_dict)
    task_dict = prepare_for_mongo(task.dict())
    await db.tasks.insert_one(task_dict)
    
    # Create notification for assignee if not assigning to self
    if task_data.assignee_id != current_user.id:
        await create_notification(
            user_id=task_data.assignee_id,
            title="New Task Assigned",
            message=f"You have been assigned a new task: {task.title}",
            task_id=task.id
        )
    
    return task

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks(
    current_user: UserResponse = Depends(get_current_user),
    status: Optional[TaskStatus] = None, 
    assignee_id: Optional[str] = None,
    client_name: Optional[str] = None,
    category: Optional[str] = None
):
    # Update overdue tasks before fetching
    await update_overdue_tasks()
    
    query = {}
    
    # Non-partners can only see their own tasks unless they're partners
    if current_user.role != UserRole.PARTNER:
        query["assignee_id"] = current_user.id
    
    if status:
        query["status"] = status
    if assignee_id:
        query["assignee_id"] = assignee_id
    if client_name:
        query["client_name"] = {"$regex": client_name, "$options": "i"}  # Case-insensitive search
    if category:
        query["category"] = category
    
    tasks = await db.tasks.find(query).sort("created_at", -1).to_list(length=None)
    return [Task(**parse_from_mongo(task)) for task in tasks]

@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str, current_user: UserResponse = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user can view this task (partners can view all, others only their own)
    if current_user.role != UserRole.PARTNER and task["assignee_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own tasks")
    
    return Task(**parse_from_mongo(task))

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate, current_user: UserResponse = Depends(get_current_user)):
    # Get the existing task
    existing_task = await db.tasks.find_one({"id": task_id})
    if not existing_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Prevent editing completed tasks (immutable once completed)
    if existing_task.get("status") == TaskStatus.COMPLETED:
        raise HTTPException(status_code=403, detail="Cannot edit completed tasks. Completed tasks are immutable.")
    
    # Check permissions: partners can edit any task, others can only update status of their own tasks
    if current_user.role != UserRole.PARTNER:
        if existing_task["assignee_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only update your own tasks")
        # Non-partners can only update status
        allowed_fields = {"status"}
        update_fields = set(k for k, v in task_update.dict().items() if v is not None)
        if not update_fields.issubset(allowed_fields):
            raise HTTPException(status_code=403, detail="You can only update task status")
    
    update_data = {k: v for k, v in task_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Store original assignee for notification comparison
    original_assignee_id = existing_task["assignee_id"]
    now_utc = datetime.now(timezone.utc)
    
    # Update assignee name if assignee_id is changed
    if "assignee_id" in update_data:
        assignee = await db.users.find_one({"id": update_data["assignee_id"]})
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee not found")
        update_data["assignee_name"] = assignee["name"]
    
    # Record status change in history
    if "status" in update_data:
        old_status = existing_task.get("status")
        new_status = update_data["status"]
        
        # Get existing status history or create new
        status_history = existing_task.get("status_history", [])
        
        # Add new status change entry
        status_entry = {
            "status": new_status,
            "previous_status": old_status,
            "changed_at": now_utc.isoformat(),
            "changed_at_ist": format_ist_datetime(now_utc),
            "changed_by": current_user.name,
            "action": "status_changed"
        }
        status_history.append(status_entry)
        update_data["status_history"] = status_history
        
        # Set completed_at when status changes to completed
        if new_status == TaskStatus.COMPLETED:
            update_data["completed_at"] = now_utc.isoformat()
    
    update_data["updated_at"] = now_utc.isoformat()
    
    result = await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    updated_task = await db.tasks.find_one({"id": task_id})
    
    # Create notifications
    if current_user.role == UserRole.PARTNER:
        # If assignee changed, notify both old and new assignee
        if "assignee_id" in update_data and update_data["assignee_id"] != original_assignee_id:
            # Notify new assignee
            if update_data["assignee_id"] != current_user.id:
                await create_notification(
                    user_id=update_data["assignee_id"],
                    title="Task Reassigned to You",
                    message=f"You have been assigned to task: {updated_task['title']}",
                    task_id=task_id
                )
            
            # Notify old assignee (if different from partner and new assignee)
            if original_assignee_id != current_user.id and original_assignee_id != update_data["assignee_id"]:
                await create_notification(
                    user_id=original_assignee_id,
                    title="Task Reassigned",
                    message=f"Task '{updated_task['title']}' has been reassigned",
                    task_id=task_id
                )
        else:
            # Task was edited but assignee didn't change, notify current assignee
            if updated_task["assignee_id"] != current_user.id:
                await create_notification(
                    user_id=updated_task["assignee_id"],
                    title="Task Updated",
                    message=f"Task '{updated_task['title']}' has been updated by {current_user.name}",
                    task_id=task_id
                )
    
    return Task(**parse_from_mongo(updated_task))

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: UserResponse = Depends(get_current_partner)):
    result = await db.tasks.delete_one({"id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

# Notification endpoints
@api_router.get("/notifications", response_model=List[Notification])
async def get_user_notifications(current_user: UserResponse = Depends(get_current_user)):
    notifications = await db.notifications.find(
        {"user_id": current_user.id}
    ).sort("created_at", -1).limit(20).to_list(length=None)
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
    categories = await db.categories.find({"active": True}).sort("name", 1).to_list(length=None)
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
    clients = await db.clients.find({"active": True}).sort("name", 1).to_list(length=None)
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
    overdue_tasks = await db.tasks.find({**task_query, "status": TaskStatus.OVERDUE}).sort("due_date", 1).to_list(length=None)
    
    # Get pending tasks for next 30 days
    today = datetime.now(timezone.utc)
    thirty_days_later = today + timedelta(days=30)
    
    pending_query = {
        **task_query,
        "status": TaskStatus.PENDING,
        "$or": [
            {"due_date": {"$lte": thirty_days_later.isoformat(), "$gte": today.isoformat()}},
            {"due_date": None},  # Include tasks without due date
            {"due_date": {"$exists": False}}
        ]
    }
    pending_tasks = await db.tasks.find(pending_query).sort("due_date", 1).to_list(length=None)
    
    # For backward compatibility, also include recent_tasks
    recent_tasks = overdue_tasks + pending_tasks
    
    # Get team performance (only for partners)
    team_stats = []
    if current_user.role == UserRole.PARTNER:
        users = await db.users.find({"active": True}).to_list(length=None)
        
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
        "pending_tasks_30days": [Task(**parse_from_mongo(task)) for task in pending_tasks],
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
    
    holidays = await db.holidays.find(query).sort("date", 1).to_list(length=None)
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
    
    locations = settings.get("locations", [])
    if settings.get("enabled") and locations:
        is_within_geofence, distance_from_office, nearest_location = check_within_any_geofence(
            attendance_data.latitude, attendance_data.longitude,
            locations, settings.get("radius_meters", 100)
        )
        
        if not is_within_geofence:
            raise HTTPException(
                status_code=400, 
                detail=f"You are {distance_from_office:.0f}m away from the nearest office ({nearest_location}). Must be within {settings.get('radius_meters', 100):.0f}m to clock in."
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
    
    locations = settings.get("locations", [])
    if locations:
        is_within_geofence, distance_from_office, nearest_location = check_within_any_geofence(
            attendance_data.latitude, attendance_data.longitude,
            locations, settings.get("radius_meters", 100)
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
    }).sort("timestamp", 1).to_list(length=None)
    
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
    }).to_list(length=None)
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
    users = await db.users.find({"active": True}).to_list(length=None)
    
    report = []
    for user in users:
        # Get attendance records for this user in the month
        records = await db.attendance.find({
            "user_id": user["id"],
            "timestamp": {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}
        }).to_list(length=None)
        
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
    }).to_list(length=None)
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
    users = await db.users.find({"active": True}).to_list(length=None)
    
    report_data = []
    for user in users:
        # Get attendance records for this user in the month
        records = await db.attendance.find({
            "user_id": user["id"],
            "timestamp": {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}
        }).to_list(length=None)
        
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
        
        # Report sheet
        df_report = pd.DataFrame(sorted(report_data, key=lambda x: x["Name"]))
        df_report.to_excel(writer, sheet_name='Attendance Report', index=False)
    
    output.seek(0)
    
    filename = f"Attendance_Report_{month_names[report_month-1]}_{report_year}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Health check
@api_router.get("/")
async def root():
    return {"message": "TaskAct API is running"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()