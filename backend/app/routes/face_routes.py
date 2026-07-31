from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from typing import Optional, Dict, Any, List
from backend.app.services.face_service import FaceService
from backend.app.repositories.face_repository import FaceRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.middleware.auth_middleware import RoleChecker

router = APIRouter(prefix="/face", tags=["Face Recognition"])
face_service = FaceService()
face_repo = FaceRepository()
user_repo = UserRepository()
student_check = RoleChecker(["student"])

@router.get("/status", response_model=Dict[str, Any])
async def get_registration_status(current_user: dict = Depends(student_check)):
    profile = await face_repo.get_profile_by_user_id(current_user["_id"])
    
    if not profile:
        return {
            "isRegistered": False,
            "registeredPoses": [],
            "registrationApprovalStatus": current_user.get("registrationApprovalStatus", "none")
        }
        
    poses = [item["pose"] for item in profile.get("embeddings", [])]
    return {
        "isRegistered": True,
        "registeredPoses": poses,
        "registrationApprovalStatus": current_user.get("registrationApprovalStatus", "none")
    }

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

@router.post("/register")
async def register_face(
    front: UploadFile = File(...),
    left: UploadFile = File(...),
    right: UploadFile = File(...),
    up: UploadFile = File(...),
    down: UploadFile = File(...),
    smile: UploadFile = File(...),
    neutral: UploadFile = File(...),
    glasses: Optional[UploadFile] = File(None),
    no_glasses: Optional[UploadFile] = File(None),
    current_user: dict = Depends(student_check)
):
    approval_status = current_user.get("registrationApprovalStatus", "none")
    if approval_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is locked. You must request and receive approval from the administrator first."
        )

    pose_files = {
        "Front": front,
        "Left": left,
        "Right": right,
        "Up": up,
        "Down": down,
        "Smile": smile,
        "Neutral": neutral
    }
    
    if glasses:
        pose_files["Glasses"] = glasses
    if no_glasses:
        pose_files["No Glasses"] = no_glasses
        
    pose_images = {}
    for pose, file_obj in pose_files.items():
        # Validate that the file is an image
        if not file_obj.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File uploaded for pose '{pose}' is not an image."
            )
        
        img_bytes = await file_obj.read()
        if len(img_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File uploaded for pose '{pose}' exceeds the 10 MB size limit."
            )
        pose_images[pose] = img_bytes
        
    try:
        profile = await face_service.register_face(current_user["_id"], pose_images)
        return {
            "message": "Face registered successfully",
            "userId": profile["userId"],
            "registeredPoses": [item["pose"] for item in profile["embeddings"]]
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/verify")
async def verify_face(
    image: UploadFile = File(...),
    device_info: str = Form("Unknown Device"),
    current_user: dict = Depends(student_check)
):
    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not an image."
        )
        
    image_bytes = await image.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded image exceeds the 10 MB size limit."
        )
    
    try:
        verified, score, confidence = await face_service.verify_face(
            current_user["_id"], 
            image_bytes, 
            device_info
        )
        
        return {
            "verified": verified,
            "similarityScore": score,
            "confidence": confidence,
            "message": "Face verified successfully" if verified else "Face verification failed. Profile mismatch."
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification pipeline error: {str(e)}"
        )

@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_student_logs(current_user: dict = Depends(student_check)):
    return await face_repo.get_logs_by_user_id(current_user["_id"])

@router.post("/request-permission")
async def request_registration_permission(current_user: dict = Depends(student_check)):
    status_val = current_user.get("registrationApprovalStatus", "none")
    if status_val == "approved":
        return {
            "message": "Permission already approved. You are ready to register your face.",
            "registrationApprovalStatus": "approved"
        }
    
    updated_user = await user_repo.update(current_user["_id"], {"registrationApprovalStatus": "pending"})
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update permission request. Please try again."
        )
    return {
        "message": "Permission request submitted successfully",
        "registrationApprovalStatus": "pending"
    }
