from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.schemas.user_schemas import (
    LoginRequest, TokenResponse, TokenRefreshRequest, 
    ForgotPasswordRequest, ResetPasswordRequest, UserProfileResponse
)
from backend.app.services.auth_service import AuthService
from backend.app.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()

@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    result = await auth_service.login_user(credentials.email, credentials.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token, refresh_token, user = result
    # Format response profile mapping
    profile = UserProfileResponse(**user)
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "bearer",
        "user": profile
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_req: TokenRefreshRequest):
    result = await auth_service.refresh_session(refresh_req.refreshToken)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    access_token, refresh_token, user = result
    profile = UserProfileResponse(**user)
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "bearer",
        "user": profile
    }

@router.post("/logout")
async def logout(refresh_req: TokenRefreshRequest):
    success = await auth_service.logout_user(refresh_req.refreshToken)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token could not be revoked or is invalid"
        )
    return {"message": "Successfully logged out"}

@router.post("/forgot-password")
async def forgot_password(forgot_req: ForgotPasswordRequest):
    # Generates a reset token and returns it in the payload.
    # In a real app this is sent via email, but we return it for V1 testing convenience.
    token = await auth_service.generate_reset_token(forgot_req.email)
    if not token:
        # Avoid user enumeration, return success even if email not found
        return {"message": "If the email is registered, a password reset token has been generated.", "resetToken": None}
    
    return {
        "message": "Password reset token generated.", 
        "resetToken": token
    }

@router.post("/reset-password")
async def reset_password(reset_req: ResetPasswordRequest):
    success = await auth_service.reset_password(reset_req.token, reset_req.newPassword)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    return {"message": "Password reset successful"}

@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    return UserProfileResponse(**current_user)
