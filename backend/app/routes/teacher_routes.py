from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from backend.app.schemas.class_schemas import ClassResponse
from backend.app.schemas.user_schemas import StudentResponse
from backend.app.repositories.user_repository import UserRepository
from backend.app.repositories.class_repository import ClassRepository
from backend.app.middleware.auth_middleware import RoleChecker

router = APIRouter(prefix="/teacher", tags=["Teacher Module"])
teacher_check = RoleChecker(["teacher"])

user_repo = UserRepository()
class_repo = ClassRepository()

@router.get("/assigned-classes", response_model=List[ClassResponse])
async def get_assigned_classes(current_teacher: dict = Depends(teacher_check)):
    # Retrieve using teacher's user ID (or their teacherId)
    # The teacher document contains `assignedClasses` which is a list of class IDs
    assigned_class_ids = current_teacher.get("assignedClasses", [])
    classes = []
    for cid in assigned_class_ids:
        c = await class_repo.get_by_id(cid)
        if c:
            classes.append(ClassResponse(**c))
    return classes

@router.get("/assigned-classes/{class_id}/students", response_model=List[StudentResponse])
async def get_class_students(class_id: str, current_teacher: dict = Depends(teacher_check)):
    # Verify the class is assigned to this teacher
    assigned_class_ids = current_teacher.get("assignedClasses", [])
    if class_id not in assigned_class_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view students in this class"
        )
        
    students = await user_repo.list_students_by_class(class_id)
    return [StudentResponse(**s) for s in students]
