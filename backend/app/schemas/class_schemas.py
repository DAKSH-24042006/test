from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ClassCreate(BaseModel):
    classCode: str = Field(..., description="E.g., AIML_C")
    department: str = Field(..., description="E.g., Artificial Intelligence & Machine Learning")
    semester: int = Field(..., description="E.g., 3")
    section: str = Field(..., description="E.g., C")
    teacherId: Optional[str] = Field(None, description="ID of the assigned teacher")

class ClassUpdate(BaseModel):
    classCode: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[str] = None
    teacherId: Optional[str] = None

class ClassResponse(BaseModel):
    id: str = Field(..., alias="_id")
    classCode: str
    department: str
    semester: int
    section: str
    teacherId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
