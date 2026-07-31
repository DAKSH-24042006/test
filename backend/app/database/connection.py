import os
import uuid
import logging
import copy
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings

logger = logging.getLogger("db_connection")

class Settings(BaseSettings):
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = "smart_attendance_v1"
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretkeyforattendanceapp2026!!!")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FACE_SIMILARITY_THRESHOLD: float = 0.50  # ArcFace Cosine Similarity Threshold
    FACE_DETECTION_THRESHOLD: float = 0.55   # Face detection confidence threshold

    class Config:
        env_file = ".env"

settings = Settings()

# === IN-MEMORY MOCK MONGODB FOR ZERO CONFIG DEMOS ===

class MockInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class MockUpdateResult:
    def __init__(self, matched_count, modified_count):
        self.matched_count = matched_count
        self.modified_count = modified_count

class MockDeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count

class MockCursor:
    def __init__(self, docs):
        self.docs = docs
        self.index = 0

    def sort(self, key, direction=1):
        if key == "timestamp":
            self.docs.sort(key=lambda x: x.get("timestamp") or 0, reverse=(direction == -1))
        return self
    
    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index < len(self.docs):
            res = self.docs[self.index]
            self.index += 1
            return res
        raise StopAsyncIteration

class MockCollection:
    def __init__(self, name):
        self.name = name
        self.data = []

    def _matches(self, doc, query):
        for k, v in query.items():
            if k == "_id":
                if str(doc.get("_id")) != str(v):
                    return False
            elif isinstance(v, dict):
                if "$in" in v:
                    val = doc.get(k)
                    if val not in v["$in"]:
                        return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    async def find_one(self, query):
        for doc in self.data:
            if self._matches(doc, query):
                return copy.deepcopy(doc)
        return None

    async def insert_one(self, doc):
        new_doc = copy.deepcopy(doc)
        if "_id" not in new_doc:
            new_doc["_id"] = ObjectId()
        self.data.append(new_doc)
        return MockInsertResult(new_doc["_id"])

    async def update_one(self, query, update):
        for doc in self.data:
            if self._matches(doc, query):
                if "$set" in update:
                    for k, v in update["$set"].items():
                        doc[k] = copy.deepcopy(v)
                if "$addToSet" in update:
                    for k, v in update["$addToSet"].items():
                        if k not in doc:
                            doc[k] = []
                        if v not in doc[k]:
                            doc[k].append(copy.deepcopy(v))
                if "$pull" in update:
                    for k, v in update["$pull"].items():
                        if k in doc and isinstance(doc[k], list):
                            if v in doc[k]:
                                doc[k].remove(v)
                return MockUpdateResult(1, 1)
        return MockUpdateResult(0, 0)

    async def update_many(self, query, update):
        count = 0
        for doc in self.data:
            if self._matches(doc, query):
                if "$set" in update:
                    for k, v in update["$set"].items():
                        doc[k] = copy.deepcopy(v)
                count += 1
        return MockUpdateResult(count, count)

    async def delete_one(self, query):
        for i, doc in enumerate(self.data):
            if self._matches(doc, query):
                self.data.pop(i)
                return MockDeleteResult(1)
        return MockDeleteResult(0)

    async def delete_many(self, query):
        initial_len = len(self.data)
        self.data = [doc for doc in self.data if not self._matches(doc, query)]
        return MockDeleteResult(initial_len - len(self.data))

    def find(self, query=None):
        if query is None:
            query = {}
        matched_docs = []
        for doc in self.data:
            if self._matches(doc, query):
                matched_docs.append(copy.deepcopy(doc))
        return MockCursor(matched_docs)

class MockDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]

# === DB ENGINE SELECTION ===

class Database:
    client = None
    db = None
    is_mock: bool = False

db_instance = Database()

async def connect_to_mongo():
    try:
        # Try establishing actual connection with 1.5 seconds timeout
        db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=1500)
        db_instance.db = db_instance.client[settings.DATABASE_NAME]
        
        # Test server availability
        await db_instance.client.admin.command('ping')
        db_instance.is_mock = False
        print(f"Connected to MongoDB at {settings.MONGODB_URL}, database: {settings.DATABASE_NAME}")
        
        # Create indexes
        try:
            await db_instance.db["face_profiles"].create_index("userId", unique=True)
            print("Unique index on 'userId' ensured for 'face_profiles' collection.")
        except Exception as idx_err:
            logger.warning(f"Could not create unique index on face_profiles: {idx_err}")
            
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB: {e}. Falling back to In-Memory Mock Database.")
        db_instance.client = None
        db_instance.db = MockDatabase()
        db_instance.is_mock = True
        print("SYSTEM LOG: Active In-Memory Mock Database initialized. Actions will not persist on backend restarts.")

async def close_mongo_connection():
    if db_instance.client and not db_instance.is_mock:
        db_instance.client.close()
        print("MongoDB connection closed")

def get_db():
    if db_instance.db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo first.")
    return db_instance.db
