"""
Authentication routes for TaskAct
Handles login, logout, password reset, OTP verification
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import random
import string
from passlib.context import CryptContext

router = APIRouter(tags=["Authentication"])

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def parse_datetime(date_value):
    """
    Safely parse a date value to datetime object.
    Handles both datetime objects (from MongoDB Atlas) and ISO strings (from local MongoDB).
    Returns None if value is None or invalid.
    """
    if date_value is None:
        return None
    try:
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, str):
            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        else:
            return None
    except Exception:
        return None


# These will be set by server.py when including the router
db = None
SECRET_KEY = None
ALGORITHM = None
ACCESS_TOKEN_EXPIRE_MINUTES = None
UserRole = None
UserResponse = None
parse_from_mongo = None
prepare_for_mongo = None
create_notification = None
logger = None


def init_auth_routes(
    _db, _secret_key, _algorithm, _token_expire, 
    _user_role, _user_response, _parse_mongo, _prepare_mongo, 
    _create_notification, _logger
):
    """Initialize auth routes with dependencies from main app"""
    global db, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
    global UserRole, UserResponse, parse_from_mongo, prepare_for_mongo
    global create_notification, logger
    
    db = _db
    SECRET_KEY = _secret_key
    ALGORITHM = _algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES = _token_expire
    UserRole = _user_role
    UserResponse = _user_response
    parse_from_mongo = _parse_mongo
    prepare_for_mongo = _prepare_mongo
    create_notification = _create_notification
    logger = _logger


# ==================== MODELS ====================

class LoginRequest(BaseModel):
    company_code: str  # 4-8 alphanumeric company code
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: "UserResponseType"  # Forward reference


class ForgotPasswordRequest(BaseModel):
    company_code: str  # Added for multi-tenant
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    company_code: str  # Added for multi-tenant
    email: EmailStr
    otp: str


class ResetPasswordWithOTPRequest(BaseModel):
    company_code: str  # Added for multi-tenant
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


class ChangeOwnPasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ==================== HELPER FUNCTIONS ====================

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


async def get_current_partner(current_user = Depends(get_current_user)):
    if current_user.role != UserRole.PARTNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only partners can perform this action"
        )
    return current_user


def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))


# ==================== ROUTES ====================

@router.post("/auth/login")
async def login(login_data: LoginRequest):
    """
    Tenant user login with company code.
    Requires: company_code, email, password
    Special handling for super_admin (TASKACT1)
    """
    # First, verify the company code (tenant)
    tenant = await db.tenants.find_one({"code": login_data.company_code.upper(), "active": True})
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid company code"
        )
    
    # Find user within the tenant
    user = await db.users.find_one({
        "email": login_data.email,
        "tenant_id": tenant["id"],
        "active": True
    })
    
    if not user or not verify_password(login_data.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if this is a super_admin login
    is_super_admin = user.get("role") == "super_admin" or tenant.get("is_admin_tenant")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user["id"],
            "tenant_id": tenant["id"],
            "is_super_admin": is_super_admin
        },
        expires_delta=access_token_expires
    )
    
    user_response = UserResponse(**parse_from_mongo(user))
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response.dict(),
        "tenant": {
            "id": tenant["id"],
            "name": tenant["name"],
            "code": tenant["code"]
        }
    }
    
    # Add super_admin flag if applicable
    if is_super_admin:
        response_data["is_super_admin"] = True
    
    return response_data


@router.get("/auth/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    # Get tenant info for the user
    user_doc = await db.users.find_one({"id": current_user.id})
    tenant_id = user_doc.get("tenant_id") if user_doc else None
    is_super_admin = user_doc.get("role") == "super_admin" if user_doc else False
    
    tenant_info = None
    if tenant_id:
        tenant = await db.tenants.find_one({"id": tenant_id})
        if tenant:
            tenant_info = {
                "id": tenant["id"],
                "name": tenant["name"],
                "code": tenant["code"]
            }
            # Check if admin tenant
            if tenant.get("is_admin_tenant"):
                is_super_admin = True
    
    response = {
        **current_user.dict(),
        "tenant": tenant_info
    }
    
    if is_super_admin:
        response["is_super_admin"] = True
    
    return response


@router.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Send OTP notification for password reset (tenant-aware)
    
    Logic:
    - Non-partner user: OTP notification goes to all partners of the same tenant
    - Partner user: OTP notification goes to OTHER partners of the same tenant AND super admin
    - Super admin user: OTP notification goes to all super admins (admin tenant users)
    """
    # First, verify the company code (tenant)
    tenant = await db.tenants.find_one({"code": request.company_code.upper(), "active": True})
    if not tenant:
        return {"message": "Password reset request submitted. Please contact your administrator for the OTP."}
    
    # Check if user exists within the tenant
    user = await db.users.find_one({"email": request.email, "tenant_id": tenant["id"]})
    if not user:
        return {"message": "Password reset request submitted. Please contact your administrator for the OTP."}
    
    # Check if user is active
    if not user.get("active", True):
        return {"message": "Password reset request submitted. Please contact your administrator for the OTP."}
    
    # Generate OTP
    otp = generate_otp(6)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Invalidate any existing OTPs for this email within the tenant
    await db.otp_records.update_many(
        {"email": request.email, "tenant_id": tenant["id"], "used": False},
        {"$set": {"used": True}}
    )
    
    # Store OTP in database with tenant_id and user info
    otp_record = OTPRecord(
        email=request.email,
        otp=otp,
        expires_at=expires_at
    )
    otp_dict = prepare_for_mongo(otp_record.dict())
    otp_dict["tenant_id"] = tenant["id"]
    otp_dict["user_id"] = user["id"]
    otp_dict["user_role"] = user.get("role", "")
    await db.otp_records.insert_one(otp_dict)
    
    user_name = user.get("name", "User")
    user_role = user.get("role", "")
    is_requesting_user_partner = user_role == "partner"
    is_super_admin_tenant = tenant.get("is_admin_tenant") or tenant.get("code") == "TASKACT1"
    
    notification_recipients = []
    
    if is_super_admin_tenant:
        # Super admin user requesting password reset
        # Send to all other super admins (other users in admin tenant)
        other_admins = await db.users.find({
            "tenant_id": tenant["id"],
            "active": True,
            "id": {"$ne": user["id"]}  # Exclude the requesting user
        }).to_list(length=5000)
        notification_recipients.extend(other_admins)
        
    elif is_requesting_user_partner:
        # Partner requesting password reset
        # Send to OTHER partners of the same tenant AND to super admin
        
        # Get other partners in the same tenant
        other_partners = await db.users.find({
            "role": "partner",
            "active": True,
            "tenant_id": tenant["id"],
            "id": {"$ne": user["id"]}  # Exclude the requesting partner
        }).to_list(length=5000)
        notification_recipients.extend(other_partners)
        
        # Get super admin users (from admin tenant)
        admin_tenant = await db.tenants.find_one({"is_admin_tenant": True, "active": True})
        if not admin_tenant:
            admin_tenant = await db.tenants.find_one({"code": "TASKACT1", "active": True})
        
        if admin_tenant:
            super_admins = await db.users.find({
                "tenant_id": admin_tenant["id"],
                "active": True
            }).to_list(length=5000)
            notification_recipients.extend(super_admins)
    else:
        # Non-partner user (Associate, Junior, Intern) requesting password reset
        # Send to ALL partners of the same tenant
        partners = await db.users.find({
            "role": "partner",
            "active": True,
            "tenant_id": tenant["id"]
        }).to_list(length=5000)
        notification_recipients.extend(partners)
    
    # Send notifications to all recipients
    for recipient in notification_recipients:
        role_label = f" ({user_role})" if user_role else ""
        await create_notification(
            user_id=recipient["id"],
            title="Password Reset OTP Request",
            message=f"{user_name}{role_label} ({request.email}) has requested a password reset. OTP: {otp} (Valid for 10 minutes)"
        )
    
    # Log for debugging
    if logger:
        logger.info(f"Password reset OTP sent for {request.email} (role: {user_role}) to {len(notification_recipients)} recipients")
    
    return {"message": "Password reset request submitted. Please contact your administrator for the OTP."}


@router.post("/auth/verify-otp")
async def verify_otp_endpoint(request: VerifyOTPRequest):
    """Verify OTP without resetting password (tenant-aware)"""
    # Verify the company code
    tenant = await db.tenants.find_one({"code": request.company_code.upper(), "active": True})
    if not tenant:
        raise HTTPException(status_code=400, detail="Invalid company code")
    
    otp_record = await db.otp_records.find_one({
        "email": request.email,
        "tenant_id": tenant["id"],
        "otp": request.otp,
        "used": False
    })
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    expires_at = parse_datetime(otp_record["expires_at"])
    if expires_at and datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")
    
    return {"message": "OTP verified successfully", "valid": True}


@router.post("/auth/reset-password")
async def reset_password_with_otp(request: ResetPasswordWithOTPRequest):
    """Reset password using OTP (tenant-aware)"""
    # Verify the company code
    tenant = await db.tenants.find_one({"code": request.company_code.upper(), "active": True})
    if not tenant:
        raise HTTPException(status_code=400, detail="Invalid company code")
    
    otp_record = await db.otp_records.find_one({
        "email": request.email,
        "tenant_id": tenant["id"],
        "otp": request.otp,
        "used": False
    })
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    expires_at = parse_datetime(otp_record["expires_at"])
    if expires_at and datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")
    
    user = await db.users.find_one({"email": request.email, "tenant_id": tenant["id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_password_hash = get_password_hash(request.new_password)
    
    await db.users.update_one(
        {"email": request.email},
        {"$set": {"password_hash": new_password_hash}}
    )
    
    await db.otp_records.update_one(
        {"id": otp_record["id"]},
        {"$set": {"used": True}}
    )
    
    await create_notification(
        user_id=user["id"],
        title="Password Reset Successful",
        message="Your password has been successfully reset. If you did not make this change, please contact support immediately."
    )
    
    return {"message": "Password reset successful. You can now login with your new password."}


@router.put("/auth/change-password")
async def change_own_password(
    password_data: ChangeOwnPasswordRequest,
    current_user = Depends(get_current_user)
):
    """Allow any user to change their own password"""
    user = await db.users.find_one({"id": current_user.id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(password_data.current_password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    new_password_hash = get_password_hash(password_data.new_password)
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"password_hash": new_password_hash}}
    )
    
    return {"message": "Password changed successfully"}


# Type alias for forward reference in LoginResponse
UserResponseType = dict
