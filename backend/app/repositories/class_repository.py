from bson import ObjectId
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.app.database.connection import get_db

class ClassRepository:
    def __init__(self):
        pass

    def _get_collection(self):
        return get_db()["classes"]

    async def get_by_id(self, class_id: str) -> Optional[Dict[str, Any]]:
        try:
            clazz = await self._get_collection().find_one({"_id": ObjectId(class_id)})
            if clazz:
                clazz["_id"] = str(clazz["_id"])
            return clazz
        except Exception:
            return None

    async def get_by_code(self, class_code: str) -> Optional[Dict[str, Any]]:
        clazz = await self._get_collection().find_one({"classCode": class_code.upper()})
        if clazz:
            clazz["_id"] = str(clazz["_id"])
        return clazz

    async def create(self, class_data: Dict[str, Any]) -> Dict[str, Any]:
        class_dict = dict(class_data)
        class_dict["classCode"] = class_dict["classCode"].upper()
        class_dict["createdAt"] = datetime.utcnow()
        class_dict["updatedAt"] = datetime.utcnow()
        
        result = await self._get_collection().insert_one(class_dict)
        class_dict["_id"] = str(result.inserted_id)
        return class_dict

    async def update(self, class_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        update_dict = dict(update_data)
        if "classCode" in update_dict and update_dict["classCode"]:
            update_dict["classCode"] = update_dict["classCode"].upper()
        update_dict["updatedAt"] = datetime.utcnow()
        
        try:
            result = await self._get_collection().update_one(
                {"_id": ObjectId(class_id)},
                {"$set": update_dict}
            )
            if result.matched_count > 0:
                return await self.get_by_id(class_id)
            return None
        except Exception:
            return None

    async def delete(self, class_id: str) -> bool:
        try:
            result = await self._get_collection().delete_one({"_id": ObjectId(class_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def list_all(self) -> List[Dict[str, Any]]:
        cursor = self._get_collection().find()
        classes = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            classes.append(doc)
        return classes

    async def list_by_teacher(self, teacher_id: str) -> List[Dict[str, Any]]:
        # Find classes assigned to this teacher (either teacher DB ID or custom teacherId)
        cursor = self._get_collection().find({"teacherId": teacher_id})
        classes = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            classes.append(doc)
        return classes
