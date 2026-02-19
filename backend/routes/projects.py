"""
Project management routes for TaskAct
Handles projects with sub-tasks, templates, and pre-defined project allocation
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import jwt

router = APIRouter(tags=["Projects"])

security = HTTPBearer()

# These will be set by server.py when including the router
db = None
SECRET_KEY = None
ALGORITHM = None
UserRole = None
UserResponse = None
TaskStatus = None
parse_from_mongo = None
prepare_for_mongo = None
logger = None


def init_projects_routes(
    _db, _secret_key, _algorithm, _user_role, _user_response,
    _task_status, _parse_mongo, _prepare_mongo, _logger
):
    """Initialize projects routes with dependencies from main app"""
    global db, SECRET_KEY, ALGORITHM, UserRole, UserResponse
    global TaskStatus, parse_from_mongo, prepare_for_mongo, logger
    
    db = _db
    SECRET_KEY = _secret_key
    ALGORITHM = _algorithm
    UserRole = _user_role
    UserResponse = _user_response
    TaskStatus = _task_status
    parse_from_mongo = _parse_mongo
    prepare_for_mongo = _prepare_mongo
    logger = _logger


# ==================== ENUMS ====================

class ProjectStatus(str, Enum):
    DRAFT = "draft"          # Project created but not allocated
    READY = "ready"          # Ready for allocation
    ALLOCATED = "allocated"  # Assigned to team member
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class TemplateScope(str, Enum):
    GLOBAL = "global"     # Super admin created, available to all tenants
    TENANT = "tenant"     # Tenant-specific template


# ==================== MODELS ====================

class SubTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    priority: str = "medium"
    order: int = 0


class SubTask(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    priority: str = "medium"
    status: str = "pending"
    order: int = 0
    completed_at: Optional[str] = None
    completed_by: Optional[str] = None


class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    category: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    sub_tasks: List[SubTaskCreate] = []
    assignee_id: Optional[str] = None  # Optional at creation (draft state)
    status: ProjectStatus = ProjectStatus.DRAFT
    from_template_id: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    assignee_id: Optional[str] = None
    status: Optional[ProjectStatus] = None


class SubTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    order: Optional[int] = None


class ProjectTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    estimated_hours: Optional[float] = None
    sub_tasks: List[SubTaskCreate] = []
    scope: TemplateScope = TemplateScope.TENANT


class Project(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    category: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    sub_tasks: List[SubTask] = []
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    creator_id: str
    creator_name: str
    status: ProjectStatus = ProjectStatus.DRAFT
    progress: float = 0.0  # Percentage of completed sub-tasks
    tenant_id: Optional[str] = None
    from_template_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    allocated_at: Optional[str] = None
    completed_at: Optional[str] = None


class ProjectTemplate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    estimated_hours: Optional[float] = None
    sub_tasks: List[SubTaskCreate] = []
    scope: TemplateScope = TemplateScope.TENANT
    tenant_id: Optional[str] = None  # None for global templates
    created_by: str
    created_at: Optional[str] = None
    active: bool = True


# ==================== HELPER FUNCTIONS ====================

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


async def get_current_partner(current_user=Depends(get_current_user)):
    if current_user.role != UserRole.PARTNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only partners can perform this action"
        )
    return current_user


async def get_tenant_id(current_user):
    """Helper to get tenant_id from current user"""
    user_doc = await db.users.find_one({"id": current_user.id})
    return user_doc.get("tenant_id") if user_doc else None


def calculate_progress(sub_tasks: list) -> float:
    """Calculate project progress based on sub-task completion"""
    if not sub_tasks:
        return 0.0
    completed = sum(1 for st in sub_tasks if st.get("status") == "completed")
    return round((completed / len(sub_tasks)) * 100, 1)


# ==================== PROJECT ROUTES ====================

@router.post("/projects")
async def create_project(project_data: ProjectCreate, current_user=Depends(get_current_user)):
    """Create a new project (can be draft/ready for allocation or directly allocated)"""
    tenant_id = await get_tenant_id(current_user)
    
    # Get assignee name if provided
    assignee_name = None
    if project_data.assignee_id:
        assignee = await db.users.find_one({
            "id": project_data.assignee_id,
            "tenant_id": tenant_id
        })
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee not found")
        assignee_name = assignee["name"]
    
    now_utc = datetime.now(timezone.utc)
    
    # Create sub-tasks with IDs
    sub_tasks = []
    for i, st in enumerate(project_data.sub_tasks):
        sub_tasks.append({
            "id": str(uuid.uuid4()),
            "title": st.title,
            "description": st.description,
            "estimated_hours": st.estimated_hours,
            "actual_hours": None,
            "priority": st.priority,
            "status": "pending",
            "order": st.order if st.order else i,
            "completed_at": None,
            "completed_by": None
        })
    
    # Determine initial status
    initial_status = project_data.status
    if project_data.assignee_id and initial_status == ProjectStatus.DRAFT:
        initial_status = ProjectStatus.ALLOCATED
    
    project_dict = {
        "id": str(uuid.uuid4()),
        "title": project_data.title,
        "description": project_data.description,
        "client_name": project_data.client_name,
        "category": project_data.category,
        "priority": project_data.priority,
        "due_date": project_data.due_date,
        "estimated_hours": project_data.estimated_hours,
        "actual_hours": None,
        "sub_tasks": sub_tasks,
        "assignee_id": project_data.assignee_id,
        "assignee_name": assignee_name,
        "creator_id": current_user.id,
        "creator_name": current_user.name,
        "status": initial_status,
        "progress": 0.0,
        "tenant_id": tenant_id,
        "from_template_id": project_data.from_template_id,
        "created_at": now_utc.isoformat(),
        "updated_at": now_utc.isoformat(),
        "allocated_at": now_utc.isoformat() if project_data.assignee_id else None,
        "completed_at": None
    }
    
    project_dict = prepare_for_mongo(project_dict)
    await db.projects.insert_one(project_dict)
    
    # Create notification for assignee if allocated
    if project_data.assignee_id and project_data.assignee_id != current_user.id:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": project_data.assignee_id,
            "title": "New Project Assigned",
            "message": f"You have been assigned a new project: {project_data.title}",
            "read": False,
            "created_at": now_utc.isoformat(),
            "project_id": project_dict["id"],
            "tenant_id": tenant_id
        }
        await db.notifications.insert_one(prepare_for_mongo(notification))
    
    logger.info(f"Project created: {project_data.title} by {current_user.name}")
    
    return Project(**parse_from_mongo(project_dict))


@router.get("/projects")
async def get_projects(
    current_user=Depends(get_current_user),
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    include_drafts: bool = True
):
    """Get all projects for the tenant"""
    tenant_id = await get_tenant_id(current_user)
    
    query = {"tenant_id": tenant_id} if tenant_id else {}
    
    # Non-partners can only see their assigned projects
    if current_user.role != UserRole.PARTNER:
        query["assignee_id"] = current_user.id
        include_drafts = False
    
    if status:
        query["status"] = status
    
    if assignee_id:
        query["assignee_id"] = assignee_id
    
    if not include_drafts:
        query["status"] = {"$nin": [ProjectStatus.DRAFT, ProjectStatus.READY]}
    
    projects = await db.projects.find(query).sort("created_at", -1).to_list(length=1000)
    return [Project(**parse_from_mongo(p)) for p in projects]


@router.get("/projects/{project_id}")
async def get_project(project_id: str, current_user=Depends(get_current_user)):
    """Get a specific project"""
    tenant_id = await get_tenant_id(current_user)
    
    query = {"id": project_id}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permission
    if current_user.role != UserRole.PARTNER and project.get("assignee_id") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own projects")
    
    return Project(**parse_from_mongo(project))


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user=Depends(get_current_user)
):
    """Update a project"""
    tenant_id = await get_tenant_id(current_user)
    
    query = {"id": project_id}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Only partners can edit projects
    if current_user.role != UserRole.PARTNER:
        raise HTTPException(status_code=403, detail="Only partners can edit projects")
    
    update_data = {k: v for k, v in project_update.dict().items() if v is not None}
    
    # If assigning to someone, update assignee_name and allocated_at
    if "assignee_id" in update_data and update_data["assignee_id"]:
        assignee = await db.users.find_one({
            "id": update_data["assignee_id"],
            "tenant_id": tenant_id
        })
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee not found")
        update_data["assignee_name"] = assignee["name"]
        
        # If not already allocated, set allocated_at
        if not project.get("allocated_at"):
            update_data["allocated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Change status if draft/ready
        if project.get("status") in [ProjectStatus.DRAFT, ProjectStatus.READY]:
            update_data["status"] = ProjectStatus.ALLOCATED
    
    # Handle status changes
    if "status" in update_data:
        if update_data["status"] == ProjectStatus.COMPLETED:
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.projects.update_one({"id": project_id}, {"$set": update_data})
    
    updated_project = await db.projects.find_one({"id": project_id})
    return Project(**parse_from_mongo(updated_project))


@router.post("/projects/{project_id}/allocate")
async def allocate_project(
    project_id: str,
    assignee_id: str,
    current_user=Depends(get_current_partner)
):
    """Allocate a project to a team member"""
    tenant_id = await get_tenant_id(current_user)
    
    query = {"id": project_id}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.get("status") not in [ProjectStatus.DRAFT, ProjectStatus.READY]:
        raise HTTPException(status_code=400, detail="Project is already allocated")
    
    assignee = await db.users.find_one({
        "id": assignee_id,
        "tenant_id": tenant_id,
        "active": True
    })
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")
    
    now_utc = datetime.now(timezone.utc)
    
    update_data = {
        "assignee_id": assignee_id,
        "assignee_name": assignee["name"],
        "status": ProjectStatus.ALLOCATED,
        "allocated_at": now_utc.isoformat(),
        "updated_at": now_utc.isoformat()
    }
    
    await db.projects.update_one({"id": project_id}, {"$set": update_data})
    
    # Create notification
    if assignee_id != current_user.id:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": assignee_id,
            "title": "New Project Assigned",
            "message": f"You have been assigned a project: {project['title']}",
            "read": False,
            "created_at": now_utc.isoformat(),
            "project_id": project_id,
            "tenant_id": tenant_id
        }
        await db.notifications.insert_one(prepare_for_mongo(notification))
    
    updated_project = await db.projects.find_one({"id": project_id})
    return Project(**parse_from_mongo(updated_project))


# ==================== SUB-TASK ROUTES ====================

@router.post("/projects/{project_id}/subtasks")
async def add_subtask(
    project_id: str,
    subtask_data: SubTaskCreate,
    current_user=Depends(get_current_user)
):
    """Add a sub-task to a project"""
    tenant_id = await get_tenant_id(current_user)
    
    query = {"id": project_id}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permission
    if current_user.role != UserRole.PARTNER and project.get("assignee_id") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only modify your own projects")
    
    new_subtask = {
        "id": str(uuid.uuid4()),
        "title": subtask_data.title,
        "description": subtask_data.description,
        "estimated_hours": subtask_data.estimated_hours,
        "actual_hours": None,
        "priority": subtask_data.priority,
        "status": "pending",
        "order": subtask_data.order if subtask_data.order else len(project.get("sub_tasks", [])),
        "completed_at": None,
        "completed_by": None
    }
    
    sub_tasks = project.get("sub_tasks", [])
    sub_tasks.append(new_subtask)
    
    progress = calculate_progress(sub_tasks)
    
    await db.projects.update_one(
        {"id": project_id},
        {
            "$set": {
                "sub_tasks": sub_tasks,
                "progress": progress,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return SubTask(**new_subtask)


@router.put("/projects/{project_id}/subtasks/{subtask_id}")
async def update_subtask(
    project_id: str,
    subtask_id: str,
    subtask_update: SubTaskUpdate,
    current_user=Depends(get_current_user)
):
    """Update a sub-task"""
    tenant_id = await get_tenant_id(current_user)
    
    query = {"id": project_id}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permission
    if current_user.role != UserRole.PARTNER and project.get("assignee_id") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only modify your own projects")
    
    sub_tasks = project.get("sub_tasks", [])
    subtask_index = next((i for i, st in enumerate(sub_tasks) if st["id"] == subtask_id), None)
    
    if subtask_index is None:
        raise HTTPException(status_code=404, detail="Sub-task not found")
    
    update_data = {k: v for k, v in subtask_update.dict().items() if v is not None}
    
    # Handle status change to completed
    if update_data.get("status") == "completed" and sub_tasks[subtask_index].get("status") != "completed":
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
        update_data["completed_by"] = current_user.name
    
    sub_tasks[subtask_index].update(update_data)
    
    progress = calculate_progress(sub_tasks)
    
    # Check if all sub-tasks are completed
    all_completed = all(st.get("status") == "completed" for st in sub_tasks)
    project_update = {
        "sub_tasks": sub_tasks,
        "progress": progress,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if all_completed and sub_tasks:
        project_update["status"] = ProjectStatus.COMPLETED
        project_update["completed_at"] = datetime.now(timezone.utc).isoformat()
        # Calculate total actual hours
        total_actual = sum(st.get("actual_hours", 0) or 0 for st in sub_tasks)
        project_update["actual_hours"] = total_actual
    
    await db.projects.update_one({"id": project_id}, {"$set": project_update})
    
    return SubTask(**sub_tasks[subtask_index])


@router.delete("/projects/{project_id}/subtasks/{subtask_id}")
async def delete_subtask(
    project_id: str,
    subtask_id: str,
    current_user=Depends(get_current_partner)
):
    """Delete a sub-task (Partners only)"""
    tenant_id = await get_tenant_id(current_user)
    
    query = {"id": project_id}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    sub_tasks = project.get("sub_tasks", [])
    sub_tasks = [st for st in sub_tasks if st["id"] != subtask_id]
    
    progress = calculate_progress(sub_tasks)
    
    await db.projects.update_one(
        {"id": project_id},
        {
            "$set": {
                "sub_tasks": sub_tasks,
                "progress": progress,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Sub-task deleted"}


# ==================== TEMPLATE ROUTES ====================

@router.post("/project-templates")
async def create_template(
    template_data: ProjectTemplateCreate,
    current_user=Depends(get_current_partner)
):
    """Create a project template"""
    tenant_id = await get_tenant_id(current_user)
    
    # Only allow global scope for super admin (check if they're impersonating)
    # For now, all partner-created templates are tenant-specific
    scope = template_data.scope
    if scope == TemplateScope.GLOBAL:
        # Check if user is super admin (impersonating)
        # For now, make it tenant-scoped
        scope = TemplateScope.TENANT
    
    template_dict = {
        "id": str(uuid.uuid4()),
        "name": template_data.name,
        "description": template_data.description,
        "category": template_data.category,
        "estimated_hours": template_data.estimated_hours,
        "sub_tasks": [st.dict() for st in template_data.sub_tasks],
        "scope": scope,
        "tenant_id": tenant_id if scope == TemplateScope.TENANT else None,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True
    }
    
    template_dict = prepare_for_mongo(template_dict)
    await db.project_templates.insert_one(template_dict)
    
    logger.info(f"Project template created: {template_data.name}")
    
    return ProjectTemplate(**parse_from_mongo(template_dict))


@router.get("/project-templates")
async def get_templates(
    current_user=Depends(get_current_user),
    include_global: bool = True
):
    """Get available project templates (tenant-specific + global)"""
    tenant_id = await get_tenant_id(current_user)
    
    # Build query to get tenant-specific and global templates
    if include_global:
        query = {
            "$or": [
                {"tenant_id": tenant_id, "active": True},
                {"scope": TemplateScope.GLOBAL, "active": True}
            ]
        }
    else:
        query = {"tenant_id": tenant_id, "active": True}
    
    templates = await db.project_templates.find(query).sort("name", 1).to_list(length=500)
    return [ProjectTemplate(**parse_from_mongo(t)) for t in templates]


@router.get("/project-templates/{template_id}")
async def get_template(template_id: str, current_user=Depends(get_current_user)):
    """Get a specific template"""
    tenant_id = await get_tenant_id(current_user)
    
    template = await db.project_templates.find_one({"id": template_id, "active": True})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check access: must be global or belong to user's tenant
    if template.get("scope") != TemplateScope.GLOBAL and template.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ProjectTemplate(**parse_from_mongo(template))


@router.post("/project-templates/{template_id}/use")
async def use_template(
    template_id: str,
    title: str,
    client_name: Optional[str] = None,
    assignee_id: Optional[str] = None,
    due_date: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Create a project from a template"""
    tenant_id = await get_tenant_id(current_user)
    
    template = await db.project_templates.find_one({"id": template_id, "active": True})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check access
    if template.get("scope") != TemplateScope.GLOBAL and template.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create project from template
    project_data = ProjectCreate(
        title=title,
        description=template.get("description"),
        client_name=client_name,
        category=template.get("category"),
        estimated_hours=template.get("estimated_hours"),
        sub_tasks=[SubTaskCreate(**st) for st in template.get("sub_tasks", [])],
        assignee_id=assignee_id,
        due_date=due_date,
        status=ProjectStatus.ALLOCATED if assignee_id else ProjectStatus.READY,
        from_template_id=template_id
    )
    
    return await create_project(project_data, current_user)


@router.delete("/project-templates/{template_id}")
async def delete_template(template_id: str, current_user=Depends(get_current_partner)):
    """Deactivate a template (soft delete)"""
    tenant_id = await get_tenant_id(current_user)
    
    template = await db.project_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Can only delete own tenant's templates
    if template.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="You can only delete your own templates")
    
    await db.project_templates.update_one(
        {"id": template_id},
        {"$set": {"active": False}}
    )
    
    return {"message": "Template deleted"}
