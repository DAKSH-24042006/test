from bson import ObjectId
from typing import Optional, Dict, Any
from datetime import datetime
from backend.app.database.connection import get_db

class SessionRepository:
    def __init__(self):
        pass

    def _get_collection(self):
        return get_db()["jwt_sessions"]

    async def create_session(self, user_id: str, refresh_token: str, expires_at: datetime) -> Dict[str, Any]:
        session_doc = {
            "userId": user_id,
            "refreshToken": refresh_token,
            "createdAt": datetime.utcnow(),
            "expiresAt": expires_at,
            "revoked": False
        }
        result = await self._get_collection().insert_one(session_doc)
        session_doc["_id"] = str(result.inserted_id)
        return session_doc

    async def get_session(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        session = await self._get_collection().find_one({"refreshToken": refresh_token})
        if session:
            session["_id"] = str(session["_id"])
        return session

    async def revoke_session(self, refresh_token: str) -> bool:
        result = await self._get_collection().update_one(
            {"refreshToken": refresh_token},
            {"$set": {"revoked": True}}
        )
        return result.modified_count > 0

    async def revoke_all_user_sessions(self, user_id: str) -> int:
        result = await self._get_collection().update_many(
            {"userId": user_id, "revoked": False},
            {"$set": {"revoked": True}}
        )
        return result.modified_count
