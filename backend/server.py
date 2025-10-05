from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Task Management API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True

class UserCreate(BaseModel):
    name: str
    email: str
    role: UserRole

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    client_name: str
    category: str
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

# API Routes

# Users endpoints
@api_router.post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    user = User(**user_data.dict())
    user_dict = prepare_for_mongo(user.dict())
    await db.users.insert_one(user_dict)
    return user

@api_router.get("/users", response_model=List[User])
async def get_users():
    users = await db.users.find({"active": True}).to_list(length=None)
    return [User(**parse_from_mongo(user)) for user in users]

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id, "active": True})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**parse_from_mongo(user))

# Tasks endpoints
@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate):
    # Get assignee and creator names
    assignee = await db.users.find_one({"id": task_data.assignee_id})
    creator = await db.users.find_one({"id": task_data.creator_id})
    
    if not assignee or not creator:
        raise HTTPException(status_code=404, detail="Assignee or creator not found")
    
    task_dict = task_data.dict()
    task_dict["assignee_name"] = assignee["name"]
    task_dict["creator_name"] = creator["name"]
    
    task = Task(**task_dict)
    task_dict = prepare_for_mongo(task.dict())
    await db.tasks.insert_one(task_dict)
    return task

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks(
    status: Optional[TaskStatus] = None, 
    assignee_id: Optional[str] = None,
    client_name: Optional[str] = None,
    category: Optional[str] = None
):
    query = {}
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
async def get_task(task_id: str):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return Task(**parse_from_mongo(task))

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate):
    update_data = {k: v for k, v in task_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
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
    return Task(**parse_from_mongo(updated_task))

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    result = await db.tasks.delete_one({"id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

# Get unique clients and categories for filtering
@api_router.get("/filters")
async def get_filters():
    # Get unique client names
    clients = await db.tasks.distinct("client_name")
    
    # Get unique categories
    categories = await db.tasks.distinct("category")
    
    return {
        "clients": sorted([client for client in clients if client]),
        "categories": sorted([category for category in categories if category])
    }

# Dashboard endpoint
@api_router.get("/dashboard")
async def get_dashboard():
    # Get counts by status
    pending_count = await db.tasks.count_documents({"status": TaskStatus.PENDING})
    in_progress_count = await db.tasks.count_documents({"status": TaskStatus.IN_PROGRESS})
    completed_count = await db.tasks.count_documents({"status": TaskStatus.COMPLETED})
    overdue_count = await db.tasks.count_documents({"status": TaskStatus.OVERDUE})
    
    # Get recent tasks
    recent_tasks = await db.tasks.find().sort("created_at", -1).limit(5).to_list(length=None)
    
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
    
    return {
        "task_counts": {
            "pending": pending_count,
            "in_progress": in_progress_count,
            "completed": completed_count,
            "overdue": overdue_count,
            "total": pending_count + in_progress_count + completed_count + overdue_count
        },
        "recent_tasks": [Task(**parse_from_mongo(task)) for task in recent_tasks],
        "team_stats": team_stats
    }

# Health check
@api_router.get("/")
async def root():
    return {"message": "Task Management API is running"}

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