from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from datetime import datetime
from backend.app.database.connection import get_db
from backend.app.schemas.user_schemas import (
    StudentCreate, StudentResponse, TeacherCreate, TeacherResponse,
    UserProfileResponse
)
from backend.app.schemas.class_schemas import ClassCreate, ClassUpdate, ClassResponse
from backend.app.repositories.user_repository import UserRepository
from backend.app.repositories.class_repository import ClassRepository
from backend.app.repositories.face_repository import FaceRepository
from backend.app.services.auth_service import AuthService
from backend.app.middleware.auth_middleware import RoleChecker

router = APIRouter(prefix="/admin", tags=["Admin Module"])
admin_check = RoleChecker(["admin"])

user_repo = UserRepository()
class_repo = ClassRepository()
face_repo = FaceRepository()
auth_service = AuthService()

# === SYSTEM OVERVIEW & STATUS ===

@router.get("/overview", response_model=Dict[str, Any], dependencies=[Depends(admin_check)])
async def get_system_overview():
    classes = await class_repo.list_all()
    teachers = await user_repo.list_by_role("teacher")
    students = await user_repo.list_by_role("student")
    profiles = await face_repo.list_all_profiles()
    
    registered_student_ids = {p["userId"] for p in profiles}
    registered_count = sum(1 for s in students if s["_id"] in registered_student_ids)
    
    return {
        "totalClasses": len(classes),
        "totalTeachers": len(teachers),
        "totalStudents": len(students),
        "registeredFacesCount": registered_count,
        "unregisteredFacesCount": len(students) - registered_count,
        "registrationPercentage": (registered_count / len(students) * 100) if students else 0.0
    }

@router.get("/face-registration-status", response_model=List[Dict[str, Any]], dependencies=[Depends(admin_check)])
async def get_face_registration_status():
    students = await user_repo.list_by_role("student")
    profiles = await face_repo.list_all_profiles()
    registered_ids = {p["userId"] for p in profiles}
    
    status_list = []
    for student in students:
        status_list.append({
            "studentId": student["_id"],
            "registrationNumber": student["registrationNumber"],
            "name": student["name"],
            "email": student["email"],
            "isRegistered": student["_id"] in registered_ids
        })
    return status_list

@router.get("/logs", response_model=List[Dict[str, Any]], dependencies=[Depends(admin_check)])
async def get_verification_logs():
    logs = await face_repo.list_all_logs()
    res = []
    for l in logs:
        user = await user_repo.get_by_id(l.get("userId"))
        res.append({
            "_id": l.get("_id"),
            "userId": l.get("userId"),
            "studentName": user.get("name") if user else "Unknown Student",
            "studentEmail": user.get("email") if user else "",
            "similarityScore": l.get("similarityScore"),
            "confidence": l.get("confidence"),
            "verificationResult": l.get("verificationResult"),
            "deviceInformation": l.get("deviceInformation"),
            "timestamp": l.get("timestamp")
        })
    return res

@router.post("/reset-biometrics", dependencies=[Depends(admin_check)])
async def reset_biometrics():
    db = get_db()
    # Delete all registered face profiles and verification logs
    await db["face_profiles"].delete_many({})
    await db["verification_logs"].delete_many({})
    # Delete all student accounts
    await db["users"].delete_many({"role": "student"})
    # Re-seed the default REG001 student
    student_data = {
        "registrationNumber": "REG001",
        "name": "Alex Mercer",
        "email": "student@smart.edu",
        "passwordHash": auth_service.hash_password("StudentPassword123"),
        "role": "student",
        "registrationApprovalStatus": "none",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
    await user_repo.create(student_data)
    return {"message": "All biometric profiles, logs, and custom student profiles have been cleared successfully."}

# === CLASS MANAGEMENT ===

@router.post("/classes", response_model=ClassResponse, dependencies=[Depends(admin_check)])
async def create_class(class_data: ClassCreate):
    existing = await class_repo.get_by_code(class_data.classCode)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Class with code {class_data.classCode} already exists"
        )
    
    # If teacherId is assigned, verify it exists and is a teacher
    if class_data.teacherId:
        teacher = await user_repo.get_by_id(class_data.teacherId)
        if not teacher or teacher.get("role") != "teacher":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned teacher does not exist"
            )
            
    res = await class_repo.create(class_data.dict())
    
    # Update teacher assignedClasses list if present
    if class_data.teacherId:
        await user_repo.add_assigned_class_to_teacher(class_data.teacherId, res["_id"])
        
    return ClassResponse(**res)

@router.get("/classes", response_model=List[ClassResponse], dependencies=[Depends(admin_check)])
async def get_classes():
    classes = await class_repo.list_all()
    return [ClassResponse(**c) for c in classes]

@router.get("/classes/{class_id}", response_model=ClassResponse, dependencies=[Depends(admin_check)])
async def get_class(class_id: str):
    clazz = await class_repo.get_by_id(class_id)
    if not clazz:
        raise HTTPException(status_code=404, detail="Class not found")
    return ClassResponse(**clazz)

@router.put("/classes/{class_id}", response_model=ClassResponse, dependencies=[Depends(admin_check)])
async def update_class(class_id: str, update_data: ClassUpdate):
    old_class = await class_repo.get_by_id(class_id)
    if not old_class:
        raise HTTPException(status_code=404, detail="Class not found")
        
    # If teacher is changing
    new_teacher_id = update_data.teacherId
    old_teacher_id = old_class.get("teacherId")
    
    if new_teacher_id is not None and new_teacher_id != old_teacher_id:
        # Verify new teacher exists
        if new_teacher_id:
            teacher = await user_repo.get_by_id(new_teacher_id)
            if not teacher or teacher.get("role") != "teacher":
                raise HTTPException(status_code=400, detail="New assigned teacher does not exist")
        
        # Remove class from old teacher
        if old_teacher_id:
            await user_repo.remove_assigned_class_from_teacher(old_teacher_id, class_id)
        # Add class to new teacher
        if new_teacher_id:
            await user_repo.add_assigned_class_to_teacher(new_teacher_id, class_id)
            
    res = await class_repo.update(class_id, update_data.dict(exclude_unset=True))
    if not res:
        raise HTTPException(status_code=404, detail="Class not found or update failed")
    return ClassResponse(**res)

@router.delete("/classes/{class_id}", dependencies=[Depends(admin_check)])
async def delete_class(class_id: str):
    clazz = await class_repo.get_by_id(class_id)
    if not clazz:
        raise HTTPException(status_code=404, detail="Class not found")
        
    # Remove assignments from teacher
    teacher_id = clazz.get("teacherId")
    if teacher_id:
        await user_repo.remove_assigned_class_from_teacher(teacher_id, class_id)
        
    # Remove reference from students
    students = await user_repo.list_students_by_class(class_id)
    for student in students:
        await user_repo.update(student["_id"], {"classId": None})
        
    success = await class_repo.delete(class_id)
    if not success:
         raise HTTPException(status_code=400, detail="Failed to delete class")
    return {"message": "Class deleted successfully"}

# === TEACHER MANAGEMENT ===

@router.post("/teachers", response_model=TeacherResponse, dependencies=[Depends(admin_check)])
async def create_teacher(teacher_data: TeacherCreate):
    existing = await user_repo.get_by_email(teacher_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    existing_id = await user_repo.get_by_teacher_id(teacher_data.teacherId)
    if existing_id:
        raise HTTPException(status_code=400, detail="Teacher with this Teacher ID already exists")

    # Hash password
    user_dict = teacher_data.dict()
    user_dict["passwordHash"] = auth_service.hash_password(user_dict.pop("password"))
    
    res = await user_repo.create(user_dict)
    
    # Assign classes if specified
    for class_id in teacher_data.assignedClasses:
        clazz = await class_repo.get_by_id(class_id)
        if clazz:
            await class_repo.update(class_id, {"teacherId": res["_id"]})
            
    return TeacherResponse(**res)

@router.get("/teachers", response_model=List[TeacherResponse], dependencies=[Depends(admin_check)])
async def get_teachers():
    teachers = await user_repo.list_by_role("teacher")
    return [TeacherResponse(**t) for t in teachers]

@router.put("/teachers/{teacher_id}", response_model=TeacherResponse, dependencies=[Depends(admin_check)])
async def update_teacher(teacher_id: str, update_data: Dict[str, Any]):
    # Allow updating basic details or password
    user = await user_repo.get_by_id(teacher_id)
    if not user or user.get("role") != "teacher":
        raise HTTPException(status_code=404, detail="Teacher not found")
        
    data = dict(update_data)
    if "password" in data and data["password"]:
        data["passwordHash"] = auth_service.hash_password(data.pop("password"))
    elif "password" in data:
        data.pop("password")
        
    res = await user_repo.update(teacher_id, data)
    return TeacherResponse(**res)

@router.delete("/teachers/{teacher_id}", dependencies=[Depends(admin_check)])
async def delete_teacher(teacher_id: str):
    teacher = await user_repo.get_by_id(teacher_id)
    if not teacher or teacher.get("role") != "teacher":
        raise HTTPException(status_code=404, detail="Teacher not found")
        
    # Unassign classes
    for class_id in teacher.get("assignedClasses", []):
        await class_repo.update(class_id, {"teacherId": None})
        
    success = await user_repo.delete(teacher_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete teacher")
    return {"message": "Teacher deleted successfully"}

# === STUDENT MANAGEMENT ===

@router.post("/students", response_model=StudentResponse, dependencies=[Depends(admin_check)])
async def create_student(student_data: StudentCreate):
    existing = await user_repo.get_by_email(student_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    existing_reg = await user_repo.get_by_registration_number(student_data.registrationNumber)
    if existing_reg:
        raise HTTPException(status_code=400, detail="Student with this Registration Number already exists")
        
    # Verify class if specified
    if student_data.classId:
        clazz = await class_repo.get_by_id(student_data.classId)
        if not clazz:
            raise HTTPException(status_code=400, detail="Specified class does not exist")
            
    user_dict = student_data.dict()
    user_dict["passwordHash"] = auth_service.hash_password(user_dict.pop("password"))
    user_dict["registrationApprovalStatus"] = "none"
    
    res = await user_repo.create(user_dict)
    return StudentResponse(**res)

@router.get("/students", response_model=List[StudentResponse], dependencies=[Depends(admin_check)])
async def get_students():
    students = await user_repo.list_by_role("student")
    return [StudentResponse(**s) for s in students]

@router.put("/students/{student_id}", response_model=StudentResponse, dependencies=[Depends(admin_check)])
async def update_student(student_id: str, update_data: Dict[str, Any]):
    user = await user_repo.get_by_id(student_id)
    if not user or user.get("role") != "student":
        raise HTTPException(status_code=404, detail="Student not found")
        
    data = dict(update_data)
    if "password" in data and data["password"]:
        data["passwordHash"] = auth_service.hash_password(data.pop("password"))
    elif "password" in data:
        data.pop("password")
        
    # Verify classId if updated
    if "classId" in data and data["classId"]:
        clazz = await class_repo.get_by_id(data["classId"])
        if not clazz:
            raise HTTPException(status_code=400, detail="Class does not exist")
            
    res = await user_repo.update(student_id, data)
    return StudentResponse(**res)

@router.delete("/students/{student_id}", dependencies=[Depends(admin_check)])
async def delete_student(student_id: str):
    student = await user_repo.get_by_id(student_id)
    if not student or student.get("role") != "student":
        raise HTTPException(status_code=404, detail="Student not found")
        
    # Clean up student's face profile and logs
    await face_repo.delete_profile(student_id)
    # Note: logs are kept or deleted, we can keep them but deleting profile is required
    
    success = await user_repo.delete(student_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete student")
    return {"message": "Student deleted successfully"}

@router.get("/registration-requests", response_model=List[StudentResponse], dependencies=[Depends(admin_check)])
async def get_registration_requests():
    db = get_db()
    cursor = db["users"].find({"role": "student", "registrationApprovalStatus": "pending"})
    requests = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        requests.append(StudentResponse(**doc))
    return requests

@router.post("/approve-registration/{student_id}", dependencies=[Depends(admin_check)])
async def approve_registration(student_id: str):
    user = await user_repo.get_by_id(student_id)
    if not user or user.get("role") != "student":
        raise HTTPException(status_code=404, detail="Student not found")
        
    await user_repo.update(student_id, {"registrationApprovalStatus": "approved"})
    return {"message": f"Face registration permission approved for student {user.get('name')}"}

@router.post("/reject-registration/{student_id}", dependencies=[Depends(admin_check)])
async def reject_registration(student_id: str):
    user = await user_repo.get_by_id(student_id)
    if not user or user.get("role") != "student":
        raise HTTPException(status_code=404, detail="Student not found")
        
    await user_repo.update(student_id, {"registrationApprovalStatus": "none"})
    return {"message": f"Face registration permission rejected/revoked for student {user.get('name')}"}
