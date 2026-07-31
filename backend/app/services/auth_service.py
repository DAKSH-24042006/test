import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from backend.app.database.connection import settings
from backend.app.repositories.user_repository import UserRepository
from backend.app.repositories.session_repository import SessionRepository

class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.session_repo = SessionRepository()

    def hash_password(self, password: str) -> str:
        pwd_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt, expire

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        user = await self.user_repo.get_by_email(email)
        if not user:
            return None
        
        if not self.verify_password(password, user["passwordHash"]):
            return None
            
        return user

    async def login_user(self, email: str, password: str) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        user = await self.authenticate_user(email, password)
        if not user:
            return None
        
        # Generate tokens
        token_data = {"sub": user["_id"], "role": user["role"], "email": user["email"]}
        access_token = self.create_access_token(data=token_data)
        refresh_token, expires_at = self.create_refresh_token(data=token_data)
        
        # Save session
        await self.session_repo.create_session(user["_id"], refresh_token, expires_at)
        
        return access_token, refresh_token, user

    async def refresh_session(self, refresh_token: str) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        # Validate refresh token structure
        try:
            payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "refresh":
                return None
            user_id = payload.get("sub")
        except JWTError:
            return None
            
        # Check in DB
        session = await self.session_repo.get_session(refresh_token)
        if not session or session["revoked"] or session["expiresAt"] < datetime.utcnow():
            return None
            
        # Retrieve user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None
            
        # Revoke old session and create a new one (Token Rotation)
        await self.session_repo.revoke_session(refresh_token)
        
        token_data = {"sub": user["_id"], "role": user["role"], "email": user["email"]}
        new_access_token = self.create_access_token(data=token_data)
        new_refresh_token, expires_at = self.create_refresh_token(data=token_data)
        
        await self.session_repo.create_session(user["_id"], new_refresh_token, expires_at)
        
        return new_access_token, new_refresh_token, user

    async def logout_user(self, refresh_token: str) -> bool:
        return await self.session_repo.revoke_session(refresh_token)

    async def generate_reset_token(self, email: str) -> Optional[str]:
        user = await self.user_repo.get_by_email(email)
        if not user:
            return None
            
        # Short lived reset token (10 mins)
        reset_data = {"sub": user["_id"], "type": "reset", "email": email}
        reset_token = jwt.encode(
            reset_data, 
            settings.JWT_SECRET, 
            algorithm=settings.JWT_ALGORITHM
        )
        return reset_token

    async def reset_password(self, token: str, new_password: str) -> bool:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "reset":
                return False
            user_id = payload.get("sub")
        except JWTError:
            return False
            
        hashed_password = self.hash_password(new_password)
        updated_user = await self.user_repo.update(user_id, {"passwordHash": hashed_password})
        
        if updated_user:
            # Revoke all sessions for this user on password reset
            await self.session_repo.revoke_all_user_sessions(user_id)
            return True
            
        return False
