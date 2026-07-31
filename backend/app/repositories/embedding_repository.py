from bson import ObjectId
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.app.database.connection import get_db

class EmbeddingRepository:
    def __init__(self):
        pass

    def _get_collection(self):
        return get_db()["embeddings"]

    async def get_by_id(self, embedding_id: str) -> Optional[Dict[str, Any]]:
        try:
            emb = await self._get_collection().find_one({"_id": ObjectId(embedding_id)})
            if emb:
                emb["embedding_id"] = str(emb["_id"])
                emb["_id"] = str(emb["_id"])
            return emb
        except Exception:
            return None

    async def get_by_student_id(self, student_id: str) -> List[Dict[str, Any]]:
        cursor = self._get_collection().find({"student_id": student_id})
        embeddings = []
        async for doc in cursor:
            doc["embedding_id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            embeddings.append(doc)
        return embeddings

    async def create(self, student_id: str, embedding: List[float]) -> Dict[str, Any]:
        emb_doc = {
            "student_id": student_id,
            "embedding": embedding,
            "created_at": datetime.utcnow()
        }
        result = await self._get_collection().insert_one(emb_doc)
        emb_doc["_id"] = str(result.inserted_id)
        emb_doc["embedding_id"] = str(result.inserted_id)
        return emb_doc

    async def delete_by_student_id(self, student_id: str) -> bool:
        result = await self._get_collection().delete_many({"student_id": student_id})
        return result.deleted_count > 0

    async def delete_by_id(self, embedding_id: str) -> bool:
        try:
            result = await self._get_collection().delete_one({"_id": ObjectId(embedding_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def count_all(self) -> int:
        return await self._get_collection().count_documents({})
