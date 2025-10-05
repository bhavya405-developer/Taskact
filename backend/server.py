from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
import jwt
from passlib.context import CryptContext
import pandas as pd
import io
from tempfile import NamedTemporaryFile

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
SECRET_KEY = "your-secret-key-change-in-production"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    message: str
    task_id: Optional[str] = None
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
def prepare_for_mongo(data):
    """Convert datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    """Parse ISO strings back to datetime objects from MongoDB"""
    if isinstance(item, dict):
        for key, value in item.items():
            if isinstance(value, str) and key.endswith(('_at', 'due_date')):
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
    notification_dict = prepare_for_mongo(notification_dict)
    await db.notifications.insert_one(notification_dict)
    return notification

async def update_overdue_tasks():
    """Automatically update tasks to overdue status if past due date"""
    current_time = datetime.now(timezone.utc)
    
    # Find tasks that are pending or on_hold and past their due date
    overdue_query = {
        "status": {"$in": [TaskStatus.PENDING, TaskStatus.ON_HOLD]},
        "due_date": {"$lt": current_time.isoformat()},
        "due_date": {"$ne": None}
    }
    
    # Update these tasks to overdue status
    result = await db.tasks.update_many(
        overdue_query,
        {"$set": {
            "status": TaskStatus.OVERDUE,
            "updated_at": current_time.isoformat()
        }}
    )
    
    return result.modified_count

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
async def get_users(current_user: UserResponse = Depends(get_current_user)):
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

# Tasks endpoints
@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate, current_user: UserResponse = Depends(get_current_user)):
    # Get assignee and creator names
    assignee = await db.users.find_one({"id": task_data.assignee_id})
    creator = await db.users.find_one({"id": current_user.id})  # Use current user as creator
    
    if not assignee or not creator:
        raise HTTPException(status_code=404, detail="Assignee or creator not found")
    
    task_dict = task_data.dict()
    task_dict["creator_id"] = current_user.id  # Set current user as creator
    task_dict["assignee_name"] = assignee["name"]
    task_dict["creator_name"] = creator["name"]
    
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
    
    # Update assignee name if assignee_id is changed
    if "assignee_id" in update_data:
        assignee = await db.users.find_one({"id": update_data["assignee_id"]})
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee not found")
        update_data["assignee_name"] = assignee["name"]
    
    # Set completed_at when status changes to completed
    if "status" in update_data and update_data["status"] == TaskStatus.COMPLETED:
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
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
    
    # Create sample data with headers
    template_data = {
        'Name': ['TechCorp Inc.', 'Global Manufacturing Ltd.', 'Healthcare Solutions Group'],
        'Company Type': ['Corporation', 'Corporation', 'LLC'],
        'Industry': ['Technology', 'Manufacturing', 'Healthcare'],
        'Contact Person': ['John Smith', 'Maria Rodriguez', 'Dr. James Wilson'],
        'Email': ['john@techcorp.com', 'maria@global.com', 'james@healthcare.com'],
        'Phone': ['+1 (555) 123-4567', '+1 (555) 987-6543', '+1 (555) 456-7890'],
        'Address': [
            '123 Tech Street, Silicon Valley, CA 94000',
            '456 Industrial Blvd, Detroit, MI 48000',
            '789 Medical Center Dr, Boston, MA 02000'
        ],
        'Notes': [
            'Major technology client',
            'Large manufacturing company',
            'Healthcare consulting firm'
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
        
        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#059669',
            'font_color': 'white',
            'border': 1
        })
        
        # Format headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Add instructions sheet
        instructions_data = {
            'Instructions': [
                '1. Fill in the client information below',
                '2. Name: Required field - unique client name',
                '3. Company Type: Corporation, LLC, Partnership, Individual, etc.',
                '4. Industry: Technology, Healthcare, Finance, Manufacturing, etc.',
                '5. Contact Person: Primary contact name',
                '6. Email: Client email address',
                '7. Phone: Client phone number',
                '8. Address: Full address including city, state, zip',
                '9. Notes: Additional information about the client',
                '10. Save the file and upload it back to import'
            ]
        }
        instructions_df = pd.DataFrame(instructions_data)
        instructions_df.to_excel(writer, sheet_name='Instructions', index=False)
    
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
                
                client_name = row['Name'].strip()
                
                # Check if client already exists
                existing = await db.clients.find_one({"name": client_name, "active": True})
                if existing:
                    errors.append(f"Row {index + 2}: Client '{client_name}' already exists")
                    error_count += 1
                    continue
                
                # Create client
                client_data = {
                    "name": client_name,
                    "company_type": row.get('Company Type', '').strip() if pd.notna(row.get('Company Type')) else None,
                    "industry": row.get('Industry', '').strip() if pd.notna(row.get('Industry')) else None,
                    "contact_person": row.get('Contact Person', '').strip() if pd.notna(row.get('Contact Person')) else None,
                    "email": row.get('Email', '').strip() if pd.notna(row.get('Email')) else None,
                    "phone": row.get('Phone', '').strip() if pd.notna(row.get('Phone')) else None,
                    "address": row.get('Address', '').strip() if pd.notna(row.get('Address')) else None,
                    "notes": row.get('Notes', '').strip() if pd.notna(row.get('Notes')) else None
                }
                
                client_dict = client_data.copy()
                client_dict["id"] = str(uuid.uuid4())
                client_dict["created_by"] = current_user.id
                client_dict["created_at"] = datetime.now(timezone.utc)
                client_dict["active"] = True
                
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
    
    # Get recent tasks
    recent_tasks = await db.tasks.find(task_query).sort("created_at", -1).limit(5).to_list(length=None)
    
    # Get team performance
    users = await db.users.find({"active": True}).to_list(length=None)
    team_stats = []
    
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
    
    # Get client analytics
    client_stats = []
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
    
    # Get category analytics
    category_stats = []
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
            "in_progress": in_progress_count,
            "completed": completed_count,
            "overdue": overdue_count,
            "total": pending_count + in_progress_count + completed_count + overdue_count
        },
        "recent_tasks": [Task(**parse_from_mongo(task)) for task in recent_tasks],
        "team_stats": team_stats,
        "client_stats": sorted(client_stats, key=lambda x: x["total_tasks"], reverse=True),
        "category_stats": sorted(category_stats, key=lambda x: x["task_count"], reverse=True)
    }

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