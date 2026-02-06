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
import os

# Get database and config from main app
from server import (
    db, 
    SECRET_KEY, 
    ALGORITHM, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    UserRole,
    UserResponse,
    parse_from_mongo,
    prepare_for_mongo,
    create_notification,
    logger
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==================== MODELS ====================

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


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


async def get_current_partner(current_user: UserResponse = Depends(get_current_user)):
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

@router.post("/login", response_model=LoginResponse)
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


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password")
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
    partners = await db.users.find({"role": "partner", "active": True}).to_list(length=5000)
    
    for partner in partners:
        await create_notification(
            user_id=partner["id"],
            title="Password Reset OTP Request",
            message=f"{user_name} ({request.email}) has requested a password reset. OTP: {otp} (Valid for 10 minutes)"
        )
    
    return {
        "message": "Password reset request submitted. Please contact your partner for the OTP."
    }


@router.post("/verify-otp")
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


@router.post("/reset-password")
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


@router.put("/change-password")
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
