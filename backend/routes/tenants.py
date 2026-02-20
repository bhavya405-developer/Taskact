"""
Tenant management routes for TaskAct Multi-Tenant Architecture
Handles tenant CRUD, super-admin operations, and tenant impersonation
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import re
import random
import string
from passlib.context import CryptContext

router = APIRouter(tags=["Tenants"])

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# These will be set by server.py when including the router
db = None
SECRET_KEY = None
ALGORITHM = None
ACCESS_TOKEN_EXPIRE_MINUTES = None
parse_from_mongo = None
prepare_for_mongo = None
logger = None


def init_tenants_routes(
    _db, _secret_key, _algorithm, _token_expire,
    _parse_mongo, _prepare_mongo, _logger
):
    """Initialize tenants routes with dependencies from main app"""
    global db, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
    global parse_from_mongo, prepare_for_mongo, logger
    
    db = _db
    SECRET_KEY = _secret_key
    ALGORITHM = _algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES = _token_expire
    parse_from_mongo = _parse_mongo
    prepare_for_mongo = _prepare_mongo
    logger = _logger


# ==================== MODELS ====================

class TenantCreate(BaseModel):
    name: str  # Company name
    code: Optional[str] = None  # 4-8 alphanumeric, auto-generated if not provided
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    plan: str = "standard"  # free, standard, premium
    max_users: int = 50
    # Partner details for auto-creation
    partner_name: Optional[str] = None
    partner_email: Optional[str] = None
    partner_password: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    plan: Optional[str] = None
    max_users: Optional[int] = None
    active: Optional[bool] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    code: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    plan: str
    max_users: int
    active: bool
    created_at: datetime
    user_count: Optional[int] = None
    task_count: Optional[int] = None


class SuperAdminCreate(BaseModel):
    name: str
    email: str
    password: str


class SuperAdminLogin(BaseModel):
    email: str
    password: str


class ImpersonateRequest(BaseModel):
    user_id: str
    tenant_id: str


# ==================== HELPER FUNCTIONS ====================

def generate_company_code(length: int = 6) -> str:
    """Generate a random alphanumeric company code (4-8 chars)"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


def validate_company_code(code: str) -> bool:
    """Validate company code format: 4-8 alphanumeric characters"""
    if not code:
        return False
    if len(code) < 4 or len(code) > 8:
        return False
    if not re.match(r'^[A-Za-z0-9]+$', code):
        return False
    return True


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES or 30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_super_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current super admin from token - supports both super_admins collection and users with super_admin role"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id: str = payload.get("sub")
        is_super_admin_flag: bool = payload.get("is_super_admin", False)
        
        if admin_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # First, check super_admins collection (old method)
    admin = await db.super_admins.find_one({"id": admin_id, "active": True})
    if admin:
        return parse_from_mongo(admin)
    
    # Then, check users collection for super_admin role
    user = await db.users.find_one({"id": admin_id, "active": True})
    if user and (user.get("role") == "super_admin" or is_super_admin_flag):
        return {
            "id": user["id"],
            "name": user.get("name", "Admin"),
            "email": user.get("email", ""),
            "role": "super_admin"
        }
    
    raise credentials_exception


# ==================== SUPER ADMIN ROUTES ====================

@router.post("/super-admin/login")
async def super_admin_login(login_data: SuperAdminLogin):
    """Super admin login - separate from tenant user login"""
    admin = await db.super_admins.find_one({"email": login_data.email, "active": True})
    if not admin or not verify_password(login_data.password, admin.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES or 60)
    access_token = create_access_token(
        data={"sub": admin["id"], "role": "super_admin"},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "admin": {
            "id": admin["id"],
            "name": admin["name"],
            "email": admin["email"],
            "role": "super_admin"
        }
    }


@router.get("/super-admin/me")
async def get_super_admin_info(admin=Depends(get_super_admin)):
    """Get current super admin info"""
    return {
        "id": admin["id"],
        "name": admin["name"],
        "email": admin["email"],
        "role": "super_admin"
    }


@router.post("/super-admin/create")
async def create_super_admin(admin_data: SuperAdminCreate):
    """Create a new super admin (only works if no super admins exist)"""
    # Check if any super admin exists
    existing_count = await db.super_admins.count_documents({})
    if existing_count > 0:
        # If super admins exist, require authentication
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin already exists. Contact existing admin."
        )
    
    # Check if email already exists
    existing = await db.super_admins.find_one({"email": admin_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    admin_dict = {
        "id": str(uuid.uuid4()),
        "name": admin_data.name,
        "email": admin_data.email,
        "password_hash": get_password_hash(admin_data.password),
        "active": True,
        "created_at": datetime.now(timezone.utc)
    }
    
    admin_dict = prepare_for_mongo(admin_dict)
    await db.super_admins.insert_one(admin_dict)
    
    return {
        "message": "Super admin created successfully",
        "admin": {
            "id": admin_dict["id"],
            "name": admin_dict["name"],
            "email": admin_dict["email"]
        }
    }


# ==================== TENANT MANAGEMENT ROUTES ====================

@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(tenant_data: TenantCreate, admin=Depends(get_super_admin)):
    """Create a new tenant (Super Admin only)"""
    # Validate or generate company code
    if tenant_data.code:
        code = tenant_data.code.upper()
        if not validate_company_code(code):
            raise HTTPException(
                status_code=400,
                detail="Company code must be 4-8 alphanumeric characters"
            )
        # Check if code already exists
        existing = await db.tenants.find_one({"code": code})
        if existing:
            raise HTTPException(status_code=400, detail="Company code already exists")
    else:
        # Generate unique code
        while True:
            code = generate_company_code(6)
            existing = await db.tenants.find_one({"code": code})
            if not existing:
                break
    
    tenant_dict = {
        "id": str(uuid.uuid4()),
        "name": tenant_data.name,
        "code": code,
        "contact_email": tenant_data.contact_email,
        "contact_phone": tenant_data.contact_phone,
        "address": tenant_data.address,
        "plan": tenant_data.plan,
        "max_users": tenant_data.max_users,
        "active": True,
        "created_at": datetime.now(timezone.utc),
        "created_by": admin["id"]
    }
    
    tenant_dict = prepare_for_mongo(tenant_dict)
    await db.tenants.insert_one(tenant_dict)
    
    logger.info(f"Tenant created: {tenant_data.name} (Code: {code})")
    
    return TenantResponse(**parse_from_mongo(tenant_dict))


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    include_inactive: bool = False,
    admin=Depends(get_super_admin)
):
    """List all tenants (Super Admin only)"""
    query = {} if include_inactive else {"active": True}
    tenants = await db.tenants.find(query).sort("name", 1).to_list(length=1000)
    
    result = []
    for tenant in tenants:
        tenant_data = parse_from_mongo(tenant)
        # Add user and task counts
        tenant_data["user_count"] = await db.users.count_documents({"tenant_id": tenant["id"]})
        tenant_data["task_count"] = await db.tasks.count_documents({"tenant_id": tenant["id"]})
        result.append(TenantResponse(**tenant_data))
    
    return result


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, admin=Depends(get_super_admin)):
    """Get a specific tenant (Super Admin only)"""
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant_data = parse_from_mongo(tenant)
    tenant_data["user_count"] = await db.users.count_documents({"tenant_id": tenant_id})
    tenant_data["task_count"] = await db.tasks.count_documents({"tenant_id": tenant_id})
    
    return TenantResponse(**tenant_data)


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_update: TenantUpdate,
    admin=Depends(get_super_admin)
):
    """Update a tenant (Super Admin only)"""
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    update_data = {k: v for k, v in tenant_update.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    update_data = prepare_for_mongo(update_data)
    
    await db.tenants.update_one({"id": tenant_id}, {"$set": update_data})
    
    updated_tenant = await db.tenants.find_one({"id": tenant_id})
    tenant_data = parse_from_mongo(updated_tenant)
    tenant_data["user_count"] = await db.users.count_documents({"tenant_id": tenant_id})
    tenant_data["task_count"] = await db.tasks.count_documents({"tenant_id": tenant_id})
    
    return TenantResponse(**tenant_data)


@router.delete("/tenants/{tenant_id}")
async def deactivate_tenant(tenant_id: str, admin=Depends(get_super_admin)):
    """Deactivate a tenant (Super Admin only) - preserves data"""
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.get("active", True):
        raise HTTPException(status_code=400, detail="Tenant is already deactivated")
    
    await db.tenants.update_one(
        {"id": tenant_id},
        {"$set": {"active": False, "deactivated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    logger.info(f"Tenant deactivated: {tenant['name']} (Code: {tenant['code']})")
    
    return {"message": f"Tenant '{tenant['name']}' has been deactivated"}


@router.put("/tenants/{tenant_id}/reactivate")
async def reactivate_tenant(tenant_id: str, admin=Depends(get_super_admin)):
    """Reactivate a deactivated tenant (Super Admin only)"""
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if tenant.get("active", True):
        raise HTTPException(status_code=400, detail="Tenant is already active")
    
    await db.tenants.update_one(
        {"id": tenant_id},
        {"$set": {"active": True}, "$unset": {"deactivated_at": ""}}
    )
    
    return {"message": f"Tenant '{tenant['name']}' has been reactivated"}


@router.delete("/tenants/{tenant_id}/permanent")
async def delete_tenant_permanently(tenant_id: str, admin=Depends(get_super_admin)):
    """
    Permanently delete a tenant and all associated data (Super Admin only)
    WARNING: This action cannot be undone!
    """
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Prevent deleting the main admin tenant
    if tenant.get("code") == "TASKACT1":
        raise HTTPException(status_code=403, detail="Cannot delete the platform admin tenant")
    
    tenant_name = tenant["name"]
    tenant_code = tenant["code"]
    
    # Delete all associated data
    # Delete users
    deleted_users = await db.users.delete_many({"tenant_id": tenant_id})
    
    # Delete tasks
    deleted_tasks = await db.tasks.delete_many({"tenant_id": tenant_id})
    
    # Delete projects
    deleted_projects = await db.projects.delete_many({"tenant_id": tenant_id})
    
    # Delete project templates (tenant-specific)
    deleted_templates = await db.project_templates.delete_many({"tenant_id": tenant_id})
    
    # Delete categories
    deleted_categories = await db.categories.delete_many({"tenant_id": tenant_id})
    
    # Delete clients
    deleted_clients = await db.clients.delete_many({"tenant_id": tenant_id})
    
    # Delete attendance records
    deleted_attendance = await db.attendance.delete_many({"tenant_id": tenant_id})
    
    # Delete timesheet entries
    deleted_timesheets = await db.timesheets.delete_many({"tenant_id": tenant_id})
    
    # Delete notifications
    deleted_notifications = await db.notifications.delete_many({"tenant_id": tenant_id})
    
    # Finally delete the tenant itself
    await db.tenants.delete_one({"id": tenant_id})
    
    logger.warning(f"Tenant PERMANENTLY DELETED: {tenant_name} (Code: {tenant_code}) by admin {admin['email']}")
    logger.info(f"Deleted data: {deleted_users.deleted_count} users, {deleted_tasks.deleted_count} tasks, "
                f"{deleted_projects.deleted_count} projects")
    
    return {
        "message": f"Tenant '{tenant_name}' and all associated data have been permanently deleted",
        "deleted": {
            "users": deleted_users.deleted_count,
            "tasks": deleted_tasks.deleted_count,
            "projects": deleted_projects.deleted_count,
            "templates": deleted_templates.deleted_count,
            "categories": deleted_categories.deleted_count,
            "clients": deleted_clients.deleted_count,
            "attendance": deleted_attendance.deleted_count,
            "timesheets": deleted_timesheets.deleted_count,
            "notifications": deleted_notifications.deleted_count
        }
    }


# ==================== TENANT USER MANAGEMENT ====================

@router.get("/tenants/{tenant_id}/users")
async def list_tenant_users(
    tenant_id: str,
    include_inactive: bool = False,
    admin=Depends(get_super_admin)
):
    """List all users in a tenant (Super Admin only)"""
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    query = {"tenant_id": tenant_id}
    if not include_inactive:
        query["active"] = True
    
    users = await db.users.find(query).to_list(length=1000)
    
    return [{
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "active": user.get("active", True),
        "created_at": user.get("created_at")
    } for user in users]


# ==================== IMPERSONATION ====================

@router.post("/super-admin/impersonate")
async def impersonate_user(
    request: ImpersonateRequest,
    admin=Depends(get_super_admin)
):
    """Impersonate a tenant user for support (Super Admin only)"""
    # Verify tenant exists
    tenant = await db.tenants.find_one({"id": request.tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Verify user exists and belongs to tenant
    user = await db.users.find_one({
        "id": request.user_id,
        "tenant_id": request.tenant_id
    })
    if not user:
        raise HTTPException(status_code=404, detail="User not found in this tenant")
    
    # Create impersonation token with special flag
    access_token_expires = timedelta(minutes=30)  # Shorter expiry for impersonation
    access_token = create_access_token(
        data={
            "sub": user["id"],
            "tenant_id": request.tenant_id,
            "impersonated_by": admin["id"],
            "is_impersonation": True
        },
        expires_delta=access_token_expires
    )
    
    logger.info(f"Super admin {admin['email']} impersonating user {user['email']} in tenant {tenant['name']}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "tenant_id": request.tenant_id,
            "tenant_name": tenant["name"],
            "tenant_code": tenant["code"]
        },
        "impersonation": True,
        "impersonated_by": admin["name"]
    }


# ==================== TENANT LOOKUP (Public) ====================

@router.get("/tenant/lookup/{code}")
async def lookup_tenant_by_code(code: str):
    """
    Public endpoint to lookup tenant by company code.
    Used during login to verify company code exists.
    Only returns minimal info (name).
    """
    tenant = await db.tenants.find_one({"code": code.upper(), "active": True})
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid company code")
    
    return {
        "name": tenant["name"],
        "code": tenant["code"]
    }


# ==================== TENANT STATISTICS ====================

@router.get("/super-admin/dashboard")
async def get_super_admin_dashboard(admin=Depends(get_super_admin)):
    """Get super admin dashboard statistics"""
    # Total tenants
    total_tenants = await db.tenants.count_documents({})
    active_tenants = await db.tenants.count_documents({"active": True})
    
    # Total users across all tenants
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"active": True})
    
    # Total tasks across all tenants
    total_tasks = await db.tasks.count_documents({})
    
    # Recent tenants
    recent_tenants = await db.tenants.find({}).sort("created_at", -1).limit(5).to_list(length=5)
    
    return {
        "statistics": {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "total_users": total_users,
            "active_users": active_users,
            "total_tasks": total_tasks
        },
        "recent_tenants": [{
            "id": t["id"],
            "name": t["name"],
            "code": t["code"],
            "created_at": t.get("created_at")
        } for t in recent_tenants]
    }
