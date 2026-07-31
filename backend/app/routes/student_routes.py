from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from backend.app.schemas.class_schemas import ClassResponse
from backend.app.schemas.face_schemas import VerificationLogResponse
from backend.app.repositories.class_repository import ClassRepository
from backend.app.repositories.face_repository import FaceRepository
from backend.app.middleware.auth_middleware import RoleChecker

router = APIRouter(prefix="/student", tags=["Student Module"])
student_check = RoleChecker(["student"])

class_repo = ClassRepository()
face_repo = FaceRepository()

@router.get("/class", response_model=Optional[ClassResponse])
async def get_my_class(current_student: dict = Depends(student_check)):
    class_id = current_student.get("classId")
    if not class_id:
        return None
        
    clazz = await class_repo.get_by_id(class_id)
    if not clazz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned class not found"
        )
    return ClassResponse(**clazz)

@router.get("/verification-logs", response_model=List[VerificationLogResponse])
async def get_my_verification_logs(current_student: dict = Depends(student_check)):
    logs = await face_repo.get_logs_by_user_id(current_student["_id"])
    return [VerificationLogResponse(**l) for l in logs]
