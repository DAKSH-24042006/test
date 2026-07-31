from bson import ObjectId
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.app.database.connection import get_db

class UserRepository:
    def __init__(self):
        # Database reference is obtained dynamically from connection
        pass

    def _get_collection(self):
        return get_db()["users"]

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            user = await self._get_collection().find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception:
            return None

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        user = await self._get_collection().find_one({"email": email.lower()})
        if user:
            user["_id"] = str(user["_id"])
        return user

    async def get_by_registration_number(self, reg_num: str) -> Optional[Dict[str, Any]]:
        user = await self._get_collection().find_one({"registrationNumber": reg_num})
        if user:
            user["_id"] = str(user["_id"])
        return user

    async def get_by_teacher_id(self, teacher_id: str) -> Optional[Dict[str, Any]]:
        user = await self._get_collection().find_one({"teacherId": teacher_id})
        if user:
            user["_id"] = str(user["_id"])
        return user

    async def get_by_admin_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        user = await self._get_collection().find_one({"adminId": admin_id})
        if user:
            user["_id"] = str(user["_id"])
        return user

    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        user_dict = dict(user_data)
        user_dict["email"] = user_dict["email"].lower()
        user_dict["createdAt"] = datetime.utcnow()
        user_dict["updatedAt"] = datetime.utcnow()
        
        result = await self._get_collection().insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        return user_dict

    async def update(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        update_dict = dict(update_data)
        update_dict["updatedAt"] = datetime.utcnow()
        
        try:
            result = await self._get_collection().update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_dict}
            )
            if result.matched_count > 0:
                return await self.get_by_id(user_id)
            return None
        except Exception:
            return None

    async def delete(self, user_id: str) -> bool:
        try:
            result = await self._get_collection().delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def list_by_role(self, role: str) -> List[Dict[str, Any]]:
        cursor = self._get_collection().find({"role": role})
        users = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            users.append(doc)
        return users

    async def list_students_by_class(self, class_id: str) -> List[Dict[str, Any]]:
        cursor = self._get_collection().find({"role": "student", "classId": class_id})
        students = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            students.append(doc)
        return students

    async def add_assigned_class_to_teacher(self, teacher_db_id: str, class_id: str) -> bool:
        try:
            result = await self._get_collection().update_one(
                {"_id": ObjectId(teacher_db_id), "role": "teacher"},
                {"$addToSet": {"assignedClasses": class_id}, "$set": {"updatedAt": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def remove_assigned_class_from_teacher(self, teacher_db_id: str, class_id: str) -> bool:
        try:
            result = await self._get_collection().update_one(
                {"_id": ObjectId(teacher_db_id), "role": "teacher"},
                {"$pull": {"assignedClasses": class_id}, "$set": {"updatedAt": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception:
            return False
