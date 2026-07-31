from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class EmbeddingItem(BaseModel):
    pose: str = Field(..., description="Pose: Front, Left, Right, Up, Down, Smile, Neutral, Glasses, No Glasses")
    embedding: List[float] = Field(..., description="512-dimensional ArcFace vector")

class FaceProfileCreate(BaseModel):
    userId: str
    embeddings: List[EmbeddingItem]

class FaceProfileResponse(BaseModel):
    id: str = Field(..., alias="_id")
    userId: str
    embeddings: List[EmbeddingItem]
    createdAt: datetime

    class Config:
        populate_by_name = True

class FaceVerificationRequest(BaseModel):
    # For 1:1 verification, we can upload the image file and check against user ID
    deviceInformation: Optional[str] = "Unknown Device"

class FaceVerificationResponse(BaseModel):
    verified: bool
    similarityScore: float
    confidence: float
    message: str

class VerificationLogResponse(BaseModel):
    id: str = Field(..., alias="_id")
    userId: str
    timestamp: datetime
    similarityScore: float
    confidence: float
    verificationResult: bool
    deviceInformation: str

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
