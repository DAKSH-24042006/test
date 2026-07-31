import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from backend.app.database.connection import settings
from backend.app.repositories.admin_repository import AdminRepository
from backend.app.repositories.session_repository import SessionRepository

class AuthService:
    def __init__(self):
        self.admin_repo = AdminRepository()
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

    async def authenticate_admin(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        admin = await self.admin_repo.get_by_email(email)
        if not admin:
            return None
        
        if not self.verify_password(password, admin["passwordHash"]):
            return None
            
        return admin

    async def login_admin(self, email: str, password: str) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        admin = await self.authenticate_admin(email, password)
        if not admin:
            return None
        
        # Generate tokens
        token_data = {"sub": admin["_id"], "role": "admin", "email": admin["email"]}
        access_token = self.create_access_token(data=token_data)
        refresh_token, expires_at = self.create_refresh_token(data=token_data)
        
        # Save session
        await self.session_repo.create_session(admin["_id"], refresh_token, expires_at)
        
        return access_token, refresh_token, admin

    async def refresh_session(self, refresh_token: str) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        try:
            payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "refresh":
                return None
            admin_id = payload.get("sub")
        except JWTError:
            return None
            
        session = await self.session_repo.get_session(refresh_token)
        if not session or session["revoked"] or session["expiresAt"] < datetime.utcnow():
            return None
            
        admin = await self.admin_repo.get_by_id(admin_id)
        if not admin:
            return None
            
        await self.session_repo.revoke_session(refresh_token)
        
        token_data = {"sub": admin["_id"], "role": "admin", "email": admin["email"]}
        new_access_token = self.create_access_token(data=token_data)
        new_refresh_token, expires_at = self.create_refresh_token(data=token_data)
        
        await self.session_repo.create_session(admin["_id"], new_refresh_token, expires_at)
        
        return new_access_token, new_refresh_token, admin

    async def logout_admin(self, refresh_token: str) -> bool:
        return await self.session_repo.revoke_session(refresh_token)
