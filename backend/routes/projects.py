"""
Project management routes for TaskAct
Projects are collections of tasks. Tasks within a project are REAL tasks
that appear in all task lists and can be managed like any other task.

Key concepts:
- Project Template: Blueprint with task definitions (NOT active tasks)
- Project: Actual project with real tasks created from template or directly
- Project Tasks: Regular tasks with project_id reference
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
    DRAFT = "draft"          # Project created but tasks not allocated
    ACTIVE = "active"        # Project with allocated tasks (in progress)
    COMPLETED = "completed"  # All tasks completed
    ON_HOLD = "on_hold"


class TemplateScope(str, Enum):
    GLOBAL = "global"     # Super admin created, available to all tenants
    TENANT = "tenant"     # Tenant-specific template


# ==================== MODELS ====================

class TaskDefinition(BaseModel):
    """Task definition for templates (blueprint, not actual task)"""
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    category: Optional[str] = None
    order: int = 0


class ProjectTemplateCreate(BaseModel):
    """Create a project template (blueprint for future projects)"""
    name: str
    description: Optional[str] = None
    client_id: Optional[str] = None
    category: Optional[str] = None
    tasks: List[TaskDefinition] = []  # Task blueprints


class ProjectTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[str] = None
    category: Optional[str] = None
    tasks: Optional[List[TaskDefinition]] = None


class TaskAllocation(BaseModel):
    """Task allocation when creating/allocating a project"""
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    category: Optional[str] = None
    assignee_id: str
    due_date: Optional[str] = None


class ProjectCreate(BaseModel):
    """Create a project - either from template or directly"""
    name: str
    description: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    category: Optional[str] = None
    due_date: str  # Required for projects
    
    # Option 1: Create from template
    template_id: Optional[str] = None
    
    # Option 2: Define tasks directly
    tasks: List[TaskAllocation] = []
    
    # Save as template option
    save_as_template: bool = False
    template_name: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    category: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[ProjectStatus] = None


# ==================== AUTH HELPERS ====================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        is_super_admin: bool = payload.get("is_super_admin", False)
        
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # For super admin, return a special user object
    if is_super_admin:
        admin = await db.super_admins.find_one({"id": user_id})
        if not admin:
            admin = await db.users.find_one({"id": user_id, "role": "super_admin"})
        if admin:
            return {
                "id": admin["id"],
                "name": admin.get("name", "Super Admin"),
                "email": admin.get("email"),
                "role": "super_admin",
                "tenant_id": None,
                "is_super_admin": True
            }
    
    user = await db.users.find_one({"id": user_id, "active": True})
    if user is None:
        raise credentials_exception
    
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "tenant_id": user.get("tenant_id") or tenant_id,
        "is_super_admin": False
    }


async def get_current_partner(current_user = Depends(get_current_user)):
    """Ensure current user is a partner or super admin"""
    if current_user["role"] not in ["partner", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only partners can perform this action"
        )
    return current_user


# ==================== TEMPLATE ROUTES ====================

@router.get("/project-templates")
async def get_project_templates(current_user = Depends(get_current_user)):
    """Get all templates available to the user (global + tenant-specific)"""
    query = {"$or": [{"scope": "global"}]}
    
    if current_user.get("tenant_id"):
        query["$or"].append({"tenant_id": current_user["tenant_id"]})
    
    templates = await db.project_templates.find(query).sort("name", 1).to_list(length=500)
    
    result = []
    for template in templates:
        t = parse_from_mongo(template)
        # Add permission info
        t["can_edit"] = can_edit_template(template, current_user)
        t["can_delete"] = can_delete_template(template, current_user)
        result.append(t)
    
    return result


def can_edit_template(template, current_user):
    """Check if user can edit a template"""
    # Super admin can edit all
    if current_user.get("is_super_admin"):
        return True
    
    # Global templates (created by super admin) cannot be edited by partners
    if template.get("scope") == "global":
        return False
    
    # Partners can edit tenant templates from their company
    if current_user["role"] == "partner":
        return template.get("tenant_id") == current_user.get("tenant_id")
    
    return False


def can_delete_template(template, current_user):
    """Check if user can delete a template"""
    return can_edit_template(template, current_user)


@router.post("/project-templates")
async def create_project_template(
    template_data: ProjectTemplateCreate,
    current_user = Depends(get_current_partner)
):
    """Create a project template"""
    is_super_admin = current_user.get("is_super_admin", False)
    
    template_dict = {
        "id": str(uuid.uuid4()),
        "name": template_data.name,
        "description": template_data.description,
        "client_id": template_data.client_id,
        "category": template_data.category,
        "tasks": [t.dict() for t in template_data.tasks],
        "scope": "global" if is_super_admin else "tenant",
        "tenant_id": None if is_super_admin else current_user.get("tenant_id"),
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_super_admin_created": is_super_admin
    }
    
    template_dict = prepare_for_mongo(template_dict)
    await db.project_templates.insert_one(template_dict)
    
    logger.info(f"Template created: {template_data.name} by {current_user['name']}")
    
    return parse_from_mongo(template_dict)


@router.put("/project-templates/{template_id}")
async def update_project_template(
    template_id: str,
    template_update: ProjectTemplateUpdate,
    current_user = Depends(get_current_partner)
):
    """Update a project template"""
    template = await db.project_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if not can_edit_template(template, current_user):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to edit this template"
        )
    
    update_data = {k: v for k, v in template_update.dict().items() if v is not None}
    if "tasks" in update_data:
        update_data["tasks"] = [t if isinstance(t, dict) else t.dict() for t in update_data["tasks"]]
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.project_templates.update_one({"id": template_id}, {"$set": update_data})
    
    updated = await db.project_templates.find_one({"id": template_id})
    return parse_from_mongo(updated)


@router.delete("/project-templates/{template_id}")
async def delete_project_template(
    template_id: str,
    current_user = Depends(get_current_partner)
):
    """Delete a project template"""
    template = await db.project_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if not can_delete_template(template, current_user):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this template"
        )
    
    await db.project_templates.delete_one({"id": template_id})
    
    logger.info(f"Template deleted: {template['name']} by {current_user['name']}")
    
    return {"message": "Template deleted successfully"}


# ==================== PROJECT ROUTES ====================

@router.get("/projects")
async def get_projects(current_user = Depends(get_current_user)):
    """Get all projects for the tenant"""
    query = {}
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    
    projects = await db.projects.find(query).sort("created_at", -1).to_list(length=500)
    
    result = []
    for project in projects:
        p = parse_from_mongo(project)
        
        # Get task counts for this project
        task_query = {"project_id": project["id"]}
        if current_user.get("tenant_id"):
            task_query["tenant_id"] = current_user["tenant_id"]
        
        total_tasks = await db.tasks.count_documents(task_query)
        completed_tasks = await db.tasks.count_documents({**task_query, "status": "completed"})
        
        p["total_tasks"] = total_tasks
        p["completed_tasks"] = completed_tasks
        p["progress"] = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Add permission info
        p["can_edit"] = can_edit_project(project, current_user)
        
        result.append(p)
    
    return result


def can_edit_project(project, current_user):
    """Check if user can edit a project"""
    # Super admin can edit all
    if current_user.get("is_super_admin"):
        return True
    
    # Partners can edit any project in their tenant
    if current_user["role"] == "partner":
        return project.get("tenant_id") == current_user.get("tenant_id")
    
    # Others can only edit their own projects
    return project.get("created_by") == current_user["id"]


@router.post("/projects")
async def create_project(
    project_data: ProjectCreate,
    current_user = Depends(get_current_partner)
):
    """
    Create a project with tasks.
    Options:
    1. Create from template (template_id provided)
    2. Create directly with task allocations (tasks provided)
    
    Optionally save as template for future use.
    """
    tenant_id = current_user.get("tenant_id")
    
    # Get client name if client_id provided
    client_name = project_data.client_name
    if project_data.client_id and not client_name:
        client = await db.clients.find_one({"id": project_data.client_id})
        if client:
            client_name = client["name"]
    
    # Create the project record
    project_id = str(uuid.uuid4())
    project_dict = {
        "id": project_id,
        "name": project_data.name,
        "description": project_data.description,
        "client_id": project_data.client_id,
        "client_name": client_name,
        "category": project_data.category,
        "due_date": project_data.due_date,
        "status": ProjectStatus.ACTIVE.value,
        "tenant_id": tenant_id,
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "from_template_id": project_data.template_id
    }
    
    # Get task definitions
    task_definitions = []
    
    if project_data.template_id:
        # Create from template
        template = await db.project_templates.find_one({"id": project_data.template_id})
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Convert template tasks to task allocations
        for i, task_def in enumerate(template.get("tasks", [])):
            if project_data.tasks and i < len(project_data.tasks):
                # Use provided allocation info (assignee, due_date)
                alloc = project_data.tasks[i]
                task_definitions.append({
                    "title": task_def.get("title"),
                    "description": task_def.get("description"),
                    "priority": task_def.get("priority", "medium"),
                    "category": task_def.get("category") or project_data.category,
                    "assignee_id": alloc.assignee_id,
                    "due_date": alloc.due_date or project_data.due_date
                })
            else:
                # No allocation provided for this task - skip or use defaults
                pass
    else:
        # Direct task creation
        for task in project_data.tasks:
            task_definitions.append({
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "category": task.category or project_data.category,
                "assignee_id": task.assignee_id,
                "due_date": task.due_date or project_data.due_date
            })
    
    # Create actual tasks in the tasks collection
    created_tasks = []
    for task_def in task_definitions:
        # Get assignee name
        assignee_name = None
        if task_def.get("assignee_id"):
            assignee = await db.users.find_one({"id": task_def["assignee_id"]})
            if assignee:
                assignee_name = assignee["name"]
        
        task_dict = {
            "id": str(uuid.uuid4()),
            "title": task_def["title"],
            "description": task_def.get("description"),
            "priority": task_def.get("priority", "medium"),
            "category": task_def.get("category"),
            "client_name": client_name,
            "client_id": project_data.client_id,
            "status": "pending",
            "due_date": task_def.get("due_date"),
            "assignee_id": task_def.get("assignee_id"),
            "assignee_name": assignee_name,
            "project_id": project_id,
            "project_name": project_data.name,
            "tenant_id": tenant_id,
            "created_by": current_user["id"],
            "creator_name": current_user["name"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        task_dict = prepare_for_mongo(task_dict)
        await db.tasks.insert_one(task_dict)
        created_tasks.append(task_dict)
    
    # Save project
    project_dict = prepare_for_mongo(project_dict)
    await db.projects.insert_one(project_dict)
    
    # Optionally save as template
    if project_data.save_as_template:
        template_name = project_data.template_name or f"Template: {project_data.name}"
        template_dict = {
            "id": str(uuid.uuid4()),
            "name": template_name,
            "description": project_data.description,
            "client_id": project_data.client_id,
            "category": project_data.category,
            "tasks": [
                {
                    "title": t["title"],
                    "description": t.get("description"),
                    "priority": t.get("priority", "medium"),
                    "category": t.get("category"),
                    "order": i
                }
                for i, t in enumerate(task_definitions)
            ],
            "scope": "tenant",
            "tenant_id": tenant_id,
            "created_by": current_user["id"],
            "created_by_name": current_user["name"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_super_admin_created": False
        }
        template_dict = prepare_for_mongo(template_dict)
        await db.project_templates.insert_one(template_dict)
    
    logger.info(f"Project created: {project_data.name} with {len(created_tasks)} tasks by {current_user['name']}")
    
    result = parse_from_mongo(project_dict)
    result["tasks"] = [parse_from_mongo(t) for t in created_tasks]
    result["total_tasks"] = len(created_tasks)
    result["completed_tasks"] = 0
    result["progress"] = 0
    
    return result


@router.get("/projects/{project_id}")
async def get_project(project_id: str, current_user = Depends(get_current_user)):
    """Get a project with its tasks"""
    query = {"id": project_id}
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all tasks for this project
    task_query = {"project_id": project_id}
    if current_user.get("tenant_id"):
        task_query["tenant_id"] = current_user["tenant_id"]
    
    tasks = await db.tasks.find(task_query).sort("created_at", 1).to_list(length=500)
    
    result = parse_from_mongo(project)
    result["tasks"] = [parse_from_mongo(t) for t in tasks]
    result["total_tasks"] = len(tasks)
    result["completed_tasks"] = len([t for t in tasks if t.get("status") == "completed"])
    result["progress"] = (result["completed_tasks"] / result["total_tasks"] * 100) if result["total_tasks"] > 0 else 0
    result["can_edit"] = can_edit_project(project, current_user)
    
    return result


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user = Depends(get_current_user)
):
    """Update a project"""
    query = {"id": project_id}
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not can_edit_project(project, current_user):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to edit this project"
        )
    
    update_data = {k: v for k, v in project_update.dict().items() if v is not None}
    
    # Get client name if client_id provided
    if "client_id" in update_data and update_data["client_id"]:
        client = await db.clients.find_one({"id": update_data["client_id"]})
        if client:
            update_data["client_name"] = client["name"]
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.projects.update_one({"id": project_id}, {"$set": update_data})
        
        # If client or category changed, update all project tasks
        if "client_name" in update_data or "category" in update_data:
            task_update = {}
            if "client_name" in update_data:
                task_update["client_name"] = update_data["client_name"]
                task_update["client_id"] = update_data.get("client_id")
            if "category" in update_data:
                task_update["category"] = update_data["category"]
            
            if task_update:
                await db.tasks.update_many({"project_id": project_id}, {"$set": task_update})
    
    updated = await db.projects.find_one({"id": project_id})
    return parse_from_mongo(updated)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, current_user = Depends(get_current_partner)):
    """Delete a project and all its tasks"""
    query = {"id": project_id}
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not can_edit_project(project, current_user):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this project"
        )
    
    # Delete all tasks associated with this project
    task_query = {"project_id": project_id}
    if current_user.get("tenant_id"):
        task_query["tenant_id"] = current_user["tenant_id"]
    
    deleted_tasks = await db.tasks.delete_many(task_query)
    
    # Delete the project
    await db.projects.delete_one({"id": project_id})
    
    logger.info(f"Project deleted: {project['name']} with {deleted_tasks.deleted_count} tasks by {current_user['name']}")
    
    return {"message": f"Project and {deleted_tasks.deleted_count} tasks deleted successfully"}


@router.post("/projects/{project_id}/tasks")
async def add_task_to_project(
    project_id: str,
    task: TaskAllocation,
    current_user = Depends(get_current_user)
):
    """Add a new task to an existing project"""
    query = {"id": project_id}
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not can_edit_project(project, current_user):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to add tasks to this project"
        )
    
    # Get assignee name
    assignee_name = None
    if task.assignee_id:
        assignee = await db.users.find_one({"id": task.assignee_id})
        if assignee:
            assignee_name = assignee["name"]
    
    task_dict = {
        "id": str(uuid.uuid4()),
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "category": task.category or project.get("category"),
        "client_name": project.get("client_name"),
        "client_id": project.get("client_id"),
        "status": "pending",
        "due_date": task.due_date or project.get("due_date"),
        "assignee_id": task.assignee_id,
        "assignee_name": assignee_name,
        "project_id": project_id,
        "project_name": project.get("name"),
        "tenant_id": current_user.get("tenant_id"),
        "created_by": current_user["id"],
        "creator_name": current_user["name"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    task_dict = prepare_for_mongo(task_dict)
    await db.tasks.insert_one(task_dict)
    
    return parse_from_mongo(task_dict)


# ==================== UTILITY ROUTES ====================

@router.get("/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str, current_user = Depends(get_current_user)):
    """Get all tasks for a project"""
    query = {"id": project_id}
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task_query = {"project_id": project_id}
    if current_user.get("tenant_id"):
        task_query["tenant_id"] = current_user["tenant_id"]
    
    tasks = await db.tasks.find(task_query).sort("created_at", 1).to_list(length=500)
    
    return [parse_from_mongo(t) for t in tasks]


@router.post("/projects/from-template/{template_id}")
async def create_project_from_template(
    template_id: str,
    project_name: str,
    due_date: str,
    client_id: Optional[str] = None,
    allocations: List[TaskAllocation] = [],
    save_as_template: bool = False,
    current_user = Depends(get_current_partner)
):
    """Create a project from a template with task allocations"""
    template = await db.project_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Build project data
    project_data = ProjectCreate(
        name=project_name,
        description=template.get("description"),
        client_id=client_id or template.get("client_id"),
        category=template.get("category"),
        due_date=due_date,
        template_id=template_id,
        tasks=allocations,
        save_as_template=save_as_template
    )
    
    return await create_project(project_data, current_user)
