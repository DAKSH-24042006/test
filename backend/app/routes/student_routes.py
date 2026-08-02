import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from pydantic import BaseModel
from typing import List, Optional
from backend.app.repositories.class_repository import ClassRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.services.face_service import FaceService
from backend.app.services.cache_manager import ClassCacheManager
from backend.app.database.connection import get_db

router = APIRouter(tags=["Student Module"])
logger = logging.getLogger("student_routes")

class_repo = ClassRepository()
student_repo = StudentRepository()
face_service = FaceService()

# === SCHEMAS ===

class ClassResponseItem(BaseModel):
    class_id: str
    class_name: str
    department: str
    semester: int
    section: str

class StudentResponseItem(BaseModel):
    student_id: str
    class_id: str
    reg_no: str
    name: str

class VerifyResponse(BaseModel):
    verified: bool
    similarityScore: float
    confidence: float
    verificationTime: float
    message: str

# === ENDPOINTS ===

@router.get("/classes", response_model=List[ClassResponseItem])
async def get_kiosk_classes():
    """
    Kiosk Endpoint: List all available classes.
    """
    classes = await class_repo.list_all()
    return [ClassResponseItem(**c) for c in classes]

@router.get("/students", response_model=List[StudentResponseItem])
async def get_kiosk_students(class_id: str = Query(..., alias="class")):
    """
    Kiosk Endpoint: List all students in a class.
    Warms up the RAM cache for the class in the background.
    """
    # Verify class exists
    clazz = await class_repo.get_by_id(class_id)
    if not clazz:
        raise HTTPException(status_code=404, detail="Class not found")
        
    # Warm up Class RAM Cache
    await ClassCacheManager.load_class_into_cache(class_id)
    
    students = await student_repo.list_by_class(class_id)
    return [StudentResponseItem(**s) for s in students]

@router.post("/verify", response_model=VerifyResponse)
async def verify_student_face(
    student_id: str = Form(...),
    class_id: str = Form(...),
    image: UploadFile = File(...),
    device_info: str = Form("Kiosk Mobile App")
):
    """
    Kiosk Endpoint: Perform 1:1 face verification using RAM cache.
    Logs the result to MongoDB.
    """
    # Verify student exists
    student = await student_repo.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")
        
    image_bytes = await image.read()
    
    try:
        verified, score, confidence, time_taken = await face_service.verify_face(
            student_id=student_id,
            class_id=class_id,
            image_bytes=image_bytes
        )
        
        # Log this attempt to database
        db = get_db()
        log_data = {
            "student_id": student_id,
            "class_id": class_id,
            "similarity_score": score,
            "confidence": confidence,
            "verified": verified,
            "device_info": device_info,
            "timestamp": datetime.utcnow()
        }
        await db["verification_logs"].insert_one(log_data)
        
        return VerifyResponse(
            verified=verified,
            similarityScore=score,
            confidence=confidence,
            verificationTime=time_taken,
            message="Face matched and verified successfully." if verified else "Face match mismatch."
        )
    except ValueError as ve:
        logger.warning(f"Verification ValueError: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during verification pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")
