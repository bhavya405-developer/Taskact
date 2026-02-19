"""
User management routes for TaskAct
Handles user CRUD, activation/deactivation, password management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone
import uuid
import jwt
from passlib.context import CryptContext

router = APIRouter(tags=["Users"])

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# These will be set by server.py when including the router
db = None
SECRET_KEY = None
ALGORITHM = None
UserRole = None
UserResponse = None
UserCreate = None
UserProfileUpdate = None
PasswordResetRequest = None
parse_from_mongo = None
prepare_for_mongo = None
create_notification = None
logger = None


def init_users_routes(
    _db, _secret_key, _algorithm,
    _user_role, _user_response, _user_create, _user_profile_update, _password_reset_request,
    _parse_mongo, _prepare_mongo, _create_notification, _logger
):
    """Initialize users routes with dependencies from main app"""
    global db, SECRET_KEY, ALGORITHM
    global UserRole, UserResponse, UserCreate, UserProfileUpdate, PasswordResetRequest
    global parse_from_mongo, prepare_for_mongo, create_notification, logger
    
    db = _db
    SECRET_KEY = _secret_key
    ALGORITHM = _algorithm
    UserRole = _user_role
    UserResponse = _user_response
    UserCreate = _user_create
    UserProfileUpdate = _user_profile_update
    PasswordResetRequest = _password_reset_request
    parse_from_mongo = _parse_mongo
    prepare_for_mongo = _prepare_mongo
    create_notification = _create_notification
    logger = _logger


# ==================== HELPER FUNCTIONS ====================

def get_password_hash(password):
    return pwd_context.hash(password)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": user_id, "active": True})
    if user is None:
        raise credentials_exception
    
    # Create response and attach tenant_id for later use
    user_response = UserResponse(**parse_from_mongo(user))
    user_response.tenant_id = user.get("tenant_id") or tenant_id
    return user_response


async def get_current_partner(current_user=Depends(get_current_user)):
    if current_user.role != UserRole.PARTNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only partners can perform this action"
        )
    return current_user


# ==================== ROUTES ====================

@router.post("/users")
async def create_user(user_data: dict, current_user=Depends(get_current_partner)):
    """Create a new user (Partners only) - within same tenant"""
    # Get tenant_id from current user
    user_doc = await db.users.find_one({"id": current_user.id})
    tenant_id = user_doc.get("tenant_id") if user_doc else None
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant not found")
    
    # Hash the password
    password_hash = get_password_hash(user_data.get("password"))
    
    # Check if email already exists within the same tenant
    existing_user = await db.users.find_one({
        "email": user_data.get("email"),
        "tenant_id": tenant_id
    })
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered in this organization")
    
    user_dict = user_data.copy()
    user_dict.pop("password", None)  # Remove plain password
    user_dict["password_hash"] = password_hash
    user_dict["id"] = str(uuid.uuid4())
    user_dict["created_at"] = datetime.now(timezone.utc)
    user_dict["active"] = True
    user_dict["tenant_id"] = tenant_id  # Add tenant_id
    
    user_dict = prepare_for_mongo(user_dict)
    await db.users.insert_one(user_dict)
    
    return UserResponse(**parse_from_mongo(user_dict))


@router.get("/users")
async def get_users(
    current_user=Depends(get_current_user),
    include_inactive: bool = False
):
    """Get all users within the same tenant. Partners can include inactive users."""
    # Get tenant_id from current user
    user_doc = await db.users.find_one({"id": current_user.id})
    tenant_id = user_doc.get("tenant_id") if user_doc else None
    
    query = {"tenant_id": tenant_id} if tenant_id else {}
    
    if not (include_inactive and current_user.role == UserRole.PARTNER):
        query["active"] = True
    
    users = await db.users.find(query).to_list(length=5000)
    return [UserResponse(**parse_from_mongo(user)) for user in users]


@router.get("/users/{user_id}")
async def get_user(user_id: str, current_user=Depends(get_current_user)):
    """Get a specific user by ID"""
    user = await db.users.find_one({"id": user_id, "active": True})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**parse_from_mongo(user))


@router.put("/users/{user_id}")
async def update_user_profile(
    user_id: str, 
    profile_update: dict, 
    current_user=Depends(get_current_partner)
):
    """Update user profile (Partners only)"""
    # Get existing user
    existing_user = await db.users.find_one({"id": user_id, "active": True})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prepare update data
    update_data = {k: v for k, v in profile_update.items() if v is not None}
    
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


@router.put("/users/{user_id}/password")
async def reset_user_password(
    user_id: str,
    password_data: dict,
    current_user=Depends(get_current_partner)
):
    """Reset a user's password (Partners only)"""
    # Verify the user exists
    user = await db.users.find_one({"id": user_id, "active": True})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash the new password
    new_password_hash = get_password_hash(password_data.get("new_password"))
    
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


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user=Depends(get_current_partner)
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


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user=Depends(get_current_partner)
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


@router.put("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: str,
    current_user=Depends(get_current_partner)
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
