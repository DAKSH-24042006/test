import logging
from typing import Dict, List, Any, Optional
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.embedding_repository import EmbeddingRepository

logger = logging.getLogger("cache_manager")

class ClassCacheManager:
    # Structure:
    # _cache = {
    #     class_id: {
    #         student_id: {
    #             "name": str,
    #             "reg_no": str,
    #             "embeddings": List[List[float]]
    #         }
    #     }
    # }
    _cache: Dict[str, Dict[str, Dict[str, Any]]] = {}

    @classmethod
    async def load_class_into_cache(cls, class_id: str) -> None:
        """
        Loads all students of a class and their embeddings from the database into RAM cache.
        """
        logger.info(f"Loading class {class_id} into RAM cache...")
        student_repo = StudentRepository()
        embedding_repo = EmbeddingRepository()

        try:
            students = await student_repo.list_by_class(class_id)
            class_data = {}
            
            for student in students:
                student_id = student["student_id"]
                embeddings_docs = await embedding_repo.get_by_student_id(student_id)
                embeddings_list = [e["embedding"] for e in embeddings_docs]
                
                class_data[student_id] = {
                    "name": student["name"],
                    "reg_no": student["reg_no"],
                    "embeddings": embeddings_list
                }
            
            cls._cache[class_id] = class_data
            logger.info(f"Class {class_id} loaded successfully with {len(class_data)} students.")
        except Exception as e:
            logger.error(f"Error loading class {class_id} into cache: {e}")
            raise

    @classmethod
    async def get_student_embeddings(cls, class_id: str, student_id: str) -> List[List[float]]:
        """
        Retrieves the cached embeddings for a given student.
        Loads the class cache lazily if it is not already loaded.
        """
        if class_id not in cls._cache:
            await cls.load_class_into_cache(class_id)
            
        class_data = cls._cache.get(class_id, {})
        student_data = class_data.get(student_id, {})
        return student_data.get("embeddings", [])

    @classmethod
    async def get_student_details(cls, class_id: str, student_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the cached student details (name, reg_no).
        Loads the class cache lazily if it is not already loaded.
        """
        if class_id not in cls._cache:
            await cls.load_class_into_cache(class_id)
            
        class_data = cls._cache.get(class_id, {})
        return class_data.get(student_id)

    @classmethod
    def invalidate_class(cls, class_id: str) -> None:
        """
        Clears the cached data for a specific class.
        It should be triggered whenever students, classes, or embeddings are modified.
        """
        if class_id in cls._cache:
            del cls._cache[class_id]
            logger.info(f"Invalidated cache for class {class_id}")
            
    @classmethod
    def clear_all(cls) -> None:
        """
        Clears the entire cache.
        """
        cls._cache.clear()
        logger.info("Cleared all class caches.")
