from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Union
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = Field(..., description="Role: admin, teacher, or student")

class UserCreate(UserBase):
    password: str

# Student schemas
class StudentCreate(UserCreate):
    registrationNumber: str
    classId: Optional[str] = None
    role: str = "student"

class StudentResponse(BaseModel):
    id: str = Field(..., alias="_id")
    registrationNumber: str
    name: str
    email: EmailStr
    role: str = "student"
    classId: Optional[str] = None
    registrationApprovalStatus: Optional[str] = "none"
    createdAt: datetime
    updatedAt: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

# Teacher schemas
class TeacherCreate(UserCreate):
    teacherId: str
    assignedClasses: List[str] = Field(default_factory=list)
    role: str = "teacher"

class TeacherResponse(BaseModel):
    id: str = Field(..., alias="_id")
    teacherId: str
    name: str
    email: EmailStr
    role: str = "teacher"
    assignedClasses: List[str]
    createdAt: datetime
    updatedAt: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

# Admin schemas
class AdminCreate(UserCreate):
    adminId: str
    role: str = "admin"

class AdminResponse(BaseModel):
    id: str = Field(..., alias="_id")
    adminId: str
    name: str
    email: EmailStr
    role: str = "admin"
    createdAt: datetime
    updatedAt: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

# Generic user response for authentication
class UserProfileResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    email: EmailStr
    role: str
    registrationNumber: Optional[str] = None
    teacherId: Optional[str] = None
    adminId: Optional[str] = None
    classId: Optional[str] = None
    assignedClasses: Optional[List[str]] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        populate_by_name = True

# Auth schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"
    user: UserProfileResponse

class TokenRefreshRequest(BaseModel):
    refreshToken: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str
