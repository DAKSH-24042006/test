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

from backend.app.services.liveness_session import LivenessSessionManager

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

class LivenessSessionRequest(BaseModel):
    student_id: str

class LivenessSessionResponse(BaseModel):
    session_id: str
    nonce: str
    challenges: List[str]
    challenge_descriptions: List[str]
    expires_in_seconds: int

class LivenessVerifyResponse(BaseModel):
    verified: bool
    livenessPassed: bool
    antiSpoofPassed: bool
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

@router.post("/start-liveness-session", response_model=LivenessSessionResponse)
async def start_liveness_session(req: LivenessSessionRequest):
    """
    Kiosk Endpoint: Initialize a new server-side liveness verification session
    with randomized challenge actions and a TTL timer.
    """
    student = await student_repo.get_by_id(req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    session = LivenessSessionManager.create_session(req.student_id, num_challenges=2)
    return LivenessSessionResponse(**session.to_client_response())

@router.post("/verify-with-liveness", response_model=LivenessVerifyResponse)
async def verify_student_face_with_liveness(
    student_id: str = Form(...),
    class_id: str = Form(...),
    session_id: str = Form(...),
    nonce: str = Form(...),
    images: List[UploadFile] = File(...),
    device_info: str = Form("Kiosk Mobile App")
):
    """
    Kiosk Endpoint: Perform multi-frame liveness detection, anti-spoofing analysis,
    single-face constraints enforcement, and 1:1 biometric matching.
    """
    student = await student_repo.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if not images or len(images) == 0:
        raise HTTPException(status_code=400, detail="No scan frames provided.")

    frames_bytes = []
    for img_file in images:
        if not img_file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File {img_file.filename} is not an image.")
        img_data = await img_file.read()
        frames_bytes.append(img_data)

    try:
        verified, liveness_passed, anti_spoof_passed, score, confidence, time_taken, message, details = await face_service.verify_face_with_liveness(
            student_id=student_id,
            class_id=class_id,
            session_id=session_id,
            nonce=nonce,
            frames_bytes=frames_bytes
        )

        # Log attempt to database
        db = get_db()
        log_data = {
            "student_id": student_id,
            "class_id": class_id,
            "session_id": session_id,
            "similarity_score": score,
            "confidence": confidence,
            "verified": verified,
            "liveness_passed": liveness_passed,
            "anti_spoof_passed": anti_spoof_passed,
            "device_info": device_info,
            "timestamp": datetime.utcnow()
        }
        await db["verification_logs"].insert_one(log_data)

        return LivenessVerifyResponse(
            verified=verified,
            livenessPassed=liveness_passed,
            antiSpoofPassed=anti_spoof_passed,
            similarityScore=score,
            confidence=confidence,
            verificationTime=time_taken,
            message=message
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during liveness verification pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")
