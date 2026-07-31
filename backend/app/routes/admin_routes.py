import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from pydantic import BaseModel, Field
from backend.app.middleware.auth_middleware import get_current_user
from backend.app.repositories.class_repository import ClassRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.embedding_repository import EmbeddingRepository
from backend.app.repositories.admin_repository import AdminRepository
from backend.app.services.face_service import FaceService
from backend.app.services.cache_manager import ClassCacheManager
from backend.app.database.connection import get_db

router = APIRouter(tags=["Admin Module"])
logger = logging.getLogger("admin_routes")

class_repo = ClassRepository()
student_repo = StudentRepository()
embedding_repo = EmbeddingRepository()
admin_repo = AdminRepository()
face_service = FaceService()

# === SCHEMAS ===

class ClassCreate(BaseModel):
    class_name: str = Field(..., description="E.g., BTech CSE")
    department: str = Field(..., description="E.g., CSE")
    semester: int = Field(..., description="E.g., 3")
    section: str = Field(..., description="E.g., A")

class ClassUpdate(BaseModel):
    class_name: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[str] = None

class ClassResponse(BaseModel):
    class_id: str
    class_name: str
    department: str
    semester: int
    section: str
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True

class StudentCreate(BaseModel):
    class_id: str = Field(..., description="Database Class ID")
    reg_no: str = Field(..., description="E.g., REG002")
    name: str = Field(..., description="E.g., Jane Doe")

class StudentUpdate(BaseModel):
    class_id: Optional[str] = None
    reg_no: Optional[str] = None
    name: Optional[str] = None

class StudentResponse(BaseModel):
    student_id: str
    class_id: str
    reg_no: str
    name: str
    is_registered: bool = False
    created_at: datetime

    class Config:
        populate_by_name = True


# === CLASSES ENDPOINTS ===

# === CLASSES ENDPOINTS ===

@router.post("/admin/classes", response_model=ClassResponse)
async def create_class(class_data: ClassCreate, current_admin: dict = Depends(get_current_user)):
    res = await class_repo.create(class_data.dict())
    return ClassResponse(**res)

@router.get("/admin/classes", response_model=List[ClassResponse])
async def get_classes(current_user: dict = Depends(get_current_user)):
    # Note: Accessible by admin. Also accessible by student (handled in student router, but registered here for alias)
    classes = await class_repo.list_all()
    return [ClassResponse(**c) for c in classes]

@router.get("/admin/classes/{class_id}", response_model=ClassResponse)
async def get_class(class_id: str, current_user: dict = Depends(get_current_user)):
    clazz = await class_repo.get_by_id(class_id)
    if not clazz:
        raise HTTPException(status_code=404, detail="Class not found")
    return ClassResponse(**clazz)

@router.put("/admin/classes/{class_id}", response_model=ClassResponse)
async def update_class(class_id: str, update_data: ClassUpdate, current_admin: dict = Depends(get_current_user)):
    res = await class_repo.update(class_id, update_data.dict(exclude_unset=True))
    if not res:
        raise HTTPException(status_code=404, detail="Class not found or update failed")
    # Invalidate Cache
    ClassCacheManager.invalidate_class(class_id)
    return ClassResponse(**res)

@router.delete("/admin/classes/{class_id}")
async def delete_class(class_id: str, current_admin: dict = Depends(get_current_user)):
    clazz = await class_repo.get_by_id(class_id)
    if not clazz:
        raise HTTPException(status_code=404, detail="Class not found")
        
    # Delete all students in this class
    students = await student_repo.list_by_class(class_id)
    for student in students:
        student_id = student["student_id"]
        await embedding_repo.delete_by_student_id(student_id)
        await student_repo.delete(student_id)
        
    success = await class_repo.delete(class_id)
    if not success:
         raise HTTPException(status_code=400, detail="Failed to delete class")
         
    # Invalidate Cache
    ClassCacheManager.invalidate_class(class_id)
    return {"message": "Class and all associated student profiles and embeddings deleted successfully."}


# === STUDENTS ENDPOINTS ===

@router.post("/admin/students", response_model=StudentResponse)
async def create_student(student_data: StudentCreate, current_admin: dict = Depends(get_current_user)):
    # Verify class exists
    clazz = await class_repo.get_by_id(student_data.class_id)
    if not clazz:
        raise HTTPException(status_code=400, detail="Specified class does not exist")

    existing = await student_repo.get_by_reg_no(student_data.reg_no)
    if existing:
        raise HTTPException(status_code=400, detail="Student with this registration number already exists")
        
    res = await student_repo.create(student_data.dict())
    
    # Invalidate Cache
    ClassCacheManager.invalidate_class(student_data.class_id)
    
    return StudentResponse(**res)

@router.get("/admin/students", response_model=List[StudentResponse])
async def get_students(class_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if class_id:
        students = await student_repo.list_by_class(class_id)
    else:
        students = await student_repo.list_all()
        
    res = []
    for s in students:
        emb_docs = await embedding_repo.get_by_student_id(s["student_id"])
        s_dict = dict(s)
        s_dict["is_registered"] = len(emb_docs) > 0
        res.append(StudentResponse(**s_dict))
    return res

@router.put("/admin/students/{student_id}", response_model=StudentResponse)
async def update_student(student_id: str, update_data: StudentUpdate, current_admin: dict = Depends(get_current_user)):
    student = await student_repo.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    old_class_id = student["class_id"]
    new_class_id = update_data.class_id or old_class_id
    
    if update_data.class_id:
        clazz = await class_repo.get_by_id(update_data.class_id)
        if not clazz:
            raise HTTPException(status_code=400, detail="Specified class does not exist")
            
    res = await student_repo.update(student_id, update_data.dict(exclude_unset=True))
    if not res:
        raise HTTPException(status_code=404, detail="Update failed")
        
    # Invalidate class caches
    ClassCacheManager.invalidate_class(old_class_id)
    if old_class_id != new_class_id:
        ClassCacheManager.invalidate_class(new_class_id)
        
    emb_docs = await embedding_repo.get_by_student_id(student_id)
    res_dict = dict(res)
    res_dict["is_registered"] = len(emb_docs) > 0
    return StudentResponse(**res_dict)

@router.delete("/admin/students/{student_id}")
async def delete_student(student_id: str, current_admin: dict = Depends(get_current_user)):
    student = await student_repo.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    class_id = student["class_id"]
    
    # Delete embeddings and student record
    await embedding_repo.delete_by_student_id(student_id)
    success = await student_repo.delete(student_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete student")
        
    # Invalidate Cache
    ClassCacheManager.invalidate_class(class_id)
    return {"message": "Student and embeddings deleted successfully."}


# === FACE REGISTRATION ENDPOINT ===

@router.post("/register-face")
async def register_face(
    student_id: str = Form(...),
    images: List[UploadFile] = File(...),
    current_admin: dict = Depends(get_current_user)
):
    student = await student_repo.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    if not images:
        raise HTTPException(status_code=400, detail="No images uploaded")

    images_bytes = []
    for img_file in images:
        if not img_file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File {img_file.filename} is not an image.")
        img_data = await img_file.read()
        images_bytes.append(img_data)
        
    try:
        result = await face_service.register_face(student_id, images_bytes)
        
        # Invalidate cache for student's class
        ClassCacheManager.invalidate_class(student["class_id"])
        
        return {
            "message": "Face registered successfully.",
            "student_id": student_id,
            "registered_count": result["registered_embeddings_count"]
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error registering face: {e}")
        raise HTTPException(status_code=500, detail=f"Internal registration error: {str(e)}")


# === WEB DASHBOARD COMPATIBILITY COMPAT HELPER ENDPOINTS ===

@router.get("/admin/overview")
async def get_system_overview(current_admin: dict = Depends(get_current_user)):
    classes = await class_repo.list_all()
    students = await student_repo.list_all()
    
    total_students = len(students)
    registered_count = 0
    for s in students:
        emb_docs = await embedding_repo.get_by_student_id(s["student_id"])
        if len(emb_docs) > 0:
            registered_count += 1
            
    return {
        "totalClasses": len(classes),
        "totalTeachers": 0, # Teachers deprecated in this version
        "totalStudents": total_students,
        "registeredFacesCount": registered_count,
        "unregisteredFacesCount": total_students - registered_count,
        "registrationPercentage": (registered_count / total_students * 100) if total_students > 0 else 0.0
    }

@router.get("/admin/face-registration-status")
async def get_face_registration_status(current_admin: dict = Depends(get_current_user)):
    students = await student_repo.list_all()
    status_list = []
    for student in students:
        emb_docs = await embedding_repo.get_by_student_id(student["student_id"])
        status_list.append({
            "studentId": student["student_id"],
            "registrationNumber": student["reg_no"],
            "name": student["name"],
            "email": f"{student['reg_no'].lower()}@smart.edu",
            "isRegistered": len(emb_docs) > 0
        })
    return status_list

@router.get("/admin/logs")
async def get_verification_logs(current_admin: dict = Depends(get_current_user)):
    # Standard logs can be fetched from verification_logs collection
    db = get_db()
    cursor = db["verification_logs"].find().sort("timestamp", -1).limit(50)
    logs = []
    async for doc in cursor:
        student = await student_repo.get_by_id(doc.get("student_id", ""))
        logs.append({
            "_id": str(doc["_id"]),
            "userId": doc.get("student_id"),
            "studentName": student["name"] if student else "Unknown Student",
            "studentEmail": f"{student['reg_no'].lower()}@smart.edu" if student else "",
            "similarityScore": doc.get("similarity_score"),
            "confidence": doc.get("confidence"),
            "verificationResult": doc.get("verified"),
            "deviceInformation": doc.get("device_info"),
            "timestamp": doc.get("timestamp")
        })
    return logs

@router.post("/admin/reset-biometrics")
async def reset_biometrics(current_admin: dict = Depends(get_current_user)):
    db = get_db()
    await db["embeddings"].delete_many({})
    await db["verification_logs"].delete_many({})
    await db["students"].delete_many({})
    await db["classes"].delete_many({})
    
    ClassCacheManager.clear_all()
    
    # Re-seed default class and student
    default_class = {
        "class_name": "BTech CSE A",
        "department": "CSE",
        "semester": 3,
        "section": "A"
    }
    c_res = await class_repo.create(default_class)
    
    default_student = {
        "class_id": c_res["class_id"],
        "reg_no": "REG001",
        "name": "Alex Mercer"
    }
    await student_repo.create(default_student)
    
    return {"message": "All biometric vectors, logs, student profiles and classes have been cleared successfully."}

@router.get("/admin/registration-requests")
async def get_registration_requests(current_admin: dict = Depends(get_current_user)):
    # Approvals deprecated: Admin registers face directly. Return empty list to keep javascript clean.
    return []

@router.post("/admin/approve-registration/{student_id}")
async def approve_registration(student_id: str, current_admin: dict = Depends(get_current_user)):
    return {"message": "Approved"}

@router.post("/admin/reject-registration/{student_id}")
async def reject_registration(student_id: str, current_admin: dict = Depends(get_current_user)):
    return {"message": "Rejected"}
