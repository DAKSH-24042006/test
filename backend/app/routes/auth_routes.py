from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from backend.app.services.auth_service import AuthService
from backend.app.middleware.auth_middleware import get_current_user

router = APIRouter(tags=["Authentication"])
auth_service = AuthService()

# Pydantic schemas for auth
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserProfileResponse(BaseModel):
    id: str = Field(..., alias="_id")
    admin_id: str
    name: str
    email: EmailStr
    role: str = "admin"
    created_at: datetime

    class Config:
        populate_by_name = True

class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"
    user: UserProfileResponse

class TokenRefreshRequest(BaseModel):
    refreshToken: str

@router.post("/auth/login", response_model=TokenResponse)
@router.post("/admin/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    result = await auth_service.login_admin(credentials.email, credentials.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token, refresh_token, admin = result
    
    # Map model keys
    admin_response = {
        "_id": admin["_id"],
        "admin_id": admin.get("admin_id", "ADM001"),
        "name": admin.get("name", "Admin"),
        "email": admin["email"],
        "role": "admin",
        "created_at": admin.get("created_at", datetime.utcnow())
    }
    
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "bearer",
        "user": UserProfileResponse(**admin_response)
    }

@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(refresh_req: TokenRefreshRequest):
    result = await auth_service.refresh_session(refresh_req.refreshToken)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    access_token, refresh_token, admin = result
    admin_response = {
        "_id": admin["_id"],
        "admin_id": admin.get("admin_id", "ADM001"),
        "name": admin.get("name", "Admin"),
        "email": admin["email"],
        "role": "admin",
        "created_at": admin.get("created_at", datetime.utcnow())
    }
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "bearer",
        "user": UserProfileResponse(**admin_response)
    }

@router.post("/auth/logout")
async def logout(refresh_req: TokenRefreshRequest):
    success = await auth_service.logout_admin(refresh_req.refreshToken)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token could not be revoked or is invalid"
        )
    return {"message": "Successfully logged out"}

@router.get("/auth/profile", response_model=UserProfileResponse)
async def get_profile(current_admin: dict = Depends(get_current_user)):
    admin_response = {
        "_id": current_admin["_id"],
        "admin_id": current_admin.get("admin_id", "ADM001"),
        "name": current_admin.get("name", "Admin"),
        "email": current_admin["email"],
        "role": "admin",
        "created_at": current_admin.get("created_at", datetime.utcnow())
    }
    return UserProfileResponse(**admin_response)
