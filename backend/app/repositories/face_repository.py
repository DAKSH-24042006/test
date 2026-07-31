from bson import ObjectId
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.app.database.connection import get_db

class FaceRepository:
    def __init__(self):
        pass

    def _get_face_collection(self):
        return get_db()["face_profiles"]

    def _get_log_collection(self):
        return get_db()["verification_logs"]

    # Face Profile operations
    async def get_profile_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        profile = await self._get_face_collection().find_one({"userId": user_id})
        if profile:
            profile["_id"] = str(profile["_id"])
        return profile

    async def create_profile(self, user_id: str, embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        profile_doc = {
            "userId": user_id,
            "embeddings": embeddings,
            "createdAt": datetime.utcnow()
        }
        result = await self._get_face_collection().insert_one(profile_doc)
        profile_doc["_id"] = str(result.inserted_id)
        return profile_doc

    async def update_profile(self, user_id: str, embeddings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        # This will replace the entire embeddings list with a new set (e.g. during re-registration)
        result = await self._get_face_collection().update_one(
            {"userId": user_id},
            {"$set": {"embeddings": embeddings, "createdAt": datetime.utcnow()}}
        )
        if result.matched_count > 0:
            return await self.get_profile_by_user_id(user_id)
        return None

    async def delete_profile(self, user_id: str) -> bool:
        result = await self._get_face_collection().delete_one({"userId": user_id})
        return result.deleted_count > 0

    async def list_all_profiles(self) -> List[Dict[str, Any]]:
        cursor = self._get_face_collection().find()
        profiles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            profiles.append(doc)
        return profiles

    # Verification Logs operations
    async def create_log(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        log_dict = dict(log_data)
        log_dict["timestamp"] = datetime.utcnow()
        result = await self._get_log_collection().insert_one(log_dict)
        log_dict["_id"] = str(result.inserted_id)
        return log_dict

    async def get_logs_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self._get_log_collection().find({"userId": user_id}).sort("timestamp", -1)
        logs = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            logs.append(doc)
        return logs

    async def list_all_logs(self) -> List[Dict[str, Any]]:
        cursor = self._get_log_collection().find().sort("timestamp", -1)
        logs = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            logs.append(doc)
        return logs
