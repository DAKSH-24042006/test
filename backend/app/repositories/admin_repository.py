from bson import ObjectId
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.app.database.connection import get_db

class AdminRepository:
    def __init__(self):
        pass

    def _get_collection(self):
        return get_db()["admins"]

    async def get_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        try:
            admin = await self._get_collection().find_one({"_id": ObjectId(admin_id)})
            if admin:
                admin["_id"] = str(admin["_id"])
            return admin
        except Exception:
            return None

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        admin = await self._get_collection().find_one({"email": email.lower()})
        if admin:
            admin["_id"] = str(admin["_id"])
        return admin

    async def get_by_admin_custom_id(self, admin_custom_id: str) -> Optional[Dict[str, Any]]:
        admin = await self._get_collection().find_one({"admin_id": admin_custom_id})
        if admin:
            admin["_id"] = str(admin["_id"])
        return admin

    async def create(self, admin_data: Dict[str, Any]) -> Dict[str, Any]:
        admin_dict = dict(admin_data)
        admin_dict["email"] = admin_dict["email"].lower()
        admin_dict["created_at"] = datetime.utcnow()
        
        result = await self._get_collection().insert_one(admin_dict)
        admin_dict["_id"] = str(result.inserted_id)
        return admin_dict

    async def update(self, admin_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        update_dict = dict(update_data)
        try:
            result = await self._get_collection().update_one(
                {"_id": ObjectId(admin_id)},
                {"$set": update_dict}
            )
            if result.matched_count > 0:
                return await self.get_by_id(admin_id)
            return None
        except Exception:
            return None

    async def delete(self, admin_id: str) -> bool:
        try:
            result = await self._get_collection().delete_one({"_id": ObjectId(admin_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def list_all(self) -> List[Dict[str, Any]]:
        cursor = self._get_collection().find()
        admins = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            admins.append(doc)
        return admins
