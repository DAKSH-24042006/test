from bson import ObjectId
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.app.database.connection import get_db

class StudentRepository:
    def __init__(self):
        pass

    def _get_collection(self):
        return get_db()["students"]

    async def get_by_id(self, student_id: str) -> Optional[Dict[str, Any]]:
        try:
            student = await self._get_collection().find_one({"_id": ObjectId(student_id)})
            if student:
                student["student_id"] = str(student["_id"])
                student["_id"] = str(student["_id"])
            return student
        except Exception:
            return None

    async def get_by_reg_no(self, reg_no: str) -> Optional[Dict[str, Any]]:
        student = await self._get_collection().find_one({"reg_no": reg_no})
        if student:
            student["student_id"] = str(student["_id"])
            student["_id"] = str(student["_id"])
        return student

    async def create(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        student_dict = dict(student_data)
        student_dict["created_at"] = datetime.utcnow()
        
        result = await self._get_collection().insert_one(student_dict)
        student_dict["_id"] = str(result.inserted_id)
        student_dict["student_id"] = str(result.inserted_id)
        return student_dict

    async def update(self, student_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        update_dict = dict(update_data)
        try:
            result = await self._get_collection().update_one(
                {"_id": ObjectId(student_id)},
                {"$set": update_dict}
            )
            if result.matched_count > 0:
                return await self.get_by_id(student_id)
            return None
        except Exception:
            return None

    async def delete(self, student_id: str) -> bool:
        try:
            result = await self._get_collection().delete_one({"_id": ObjectId(student_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def list_all(self) -> List[Dict[str, Any]]:
        cursor = self._get_collection().find()
        students = []
        async for doc in cursor:
            doc["student_id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            students.append(doc)
        return students

    async def list_by_class(self, class_id: str) -> List[Dict[str, Any]]:
        cursor = self._get_collection().find({"class_id": class_id})
        students = []
        async for doc in cursor:
            doc["student_id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            students.append(doc)
        return students
