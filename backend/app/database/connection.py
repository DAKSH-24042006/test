import os
import uuid
import logging
import copy
import json
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings

logger = logging.getLogger("db_connection")

def _find_env_file() -> str:
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        ".env"
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return ".env"

_env_path = _find_env_file()

class Settings(BaseSettings):
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "smart_attendance_v1")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretkeyforattendanceapp2026!!!")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days token validity for convenience
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    FACE_SIMILARITY_THRESHOLD: float = 0.58  # ArcFace Cosine Similarity Threshold
    FACE_DETECTION_THRESHOLD: float = 0.55   # Face detection confidence threshold

    # Anti-Spoofing & Liveness Detection Settings
    ANTI_SPOOF_THRESHOLD: float = 0.80       # MiniFASNet liveness confidence threshold
    LIVENESS_SESSION_TTL: int = 60           # Session expiry in seconds
    MIN_LIVENESS_FRAMES: int = 3             # Minimum frames for liveness verification
    MAX_LIVENESS_FRAMES: int = 8             # Maximum frames accepted
    MOIRE_DETECTION_ENABLED: bool = True     # Enable moiré pattern detection (screen replay defense)
    MULTI_FRAME_CONSISTENCY_ENABLED: bool = True  # Enable frame-to-frame consistency analysis

    class Config:
        env_file = _env_path

settings = Settings()


# === FILE-PERSISTED MOCK MONGODB FOR ZERO CONFIG DEMOS ===

MOCK_DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mock_db.json")

def _json_serialize(obj):
    if isinstance(obj, ObjectId):
        return {"$oid": str(obj)}
    if isinstance(obj, datetime):
        return {"$date": obj.isoformat()}
    raise TypeError(f"Type {type(obj)} not serializable")

def _json_deserialize(dct):
    if "$oid" in dct:
        return ObjectId(dct["$oid"])
    if "$date" in dct:
        try:
            return datetime.fromisoformat(dct["$date"])
        except ValueError:
            return dct["$date"]
    return dct

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
        if key == "timestamp" or key == "created_at":
            self.docs.sort(key=lambda x: str(x.get(key) or ""), reverse=(direction == -1))
        return self

    def limit(self, count):
        self.docs = self.docs[:count]
        return self

    def skip(self, count):
        self.docs = self.docs[count:]
        return self

    async def to_list(self, length=None):
        if length is not None:
            return copy.deepcopy(self.docs[:length])
        return copy.deepcopy(self.docs)
    
    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index < len(self.docs):
            res = self.docs[self.index]
            self.index += 1
            return res
        raise StopAsyncIteration

class MockCollection:
    def __init__(self, name, db=None):
        self.name = name
        self.data = []
        self.db = db

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

    def _notify_change(self):
        if self.db:
            self.db.save_to_disk()

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
        self._notify_change()
        return MockInsertResult(new_doc["_id"])

    async def insert_many(self, docs):
        inserted_ids = []
        for doc in docs:
            new_doc = copy.deepcopy(doc)
            if "_id" not in new_doc:
                new_doc["_id"] = ObjectId()
            self.data.append(new_doc)
            inserted_ids.append(new_doc["_id"])
        self._notify_change()
        return inserted_ids

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
                self._notify_change()
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
        if count > 0:
            self._notify_change()
        return MockUpdateResult(count, count)

    async def delete_one(self, query):
        for i, doc in enumerate(self.data):
            if self._matches(doc, query):
                self.data.pop(i)
                self._notify_change()
                return MockDeleteResult(1)
        return MockDeleteResult(0)

    async def delete_many(self, query):
        initial_len = len(self.data)
        self.data = [doc for doc in self.data if not self._matches(doc, query)]
        deleted = initial_len - len(self.data)
        if deleted > 0:
            self._notify_change()
        return MockDeleteResult(deleted)

    def find(self, query=None):
        if query is None:
            query = {}
        matched_docs = []
        for doc in self.data:
            if self._matches(doc, query):
                matched_docs.append(copy.deepcopy(doc))
        return MockCursor(matched_docs)

    async def count_documents(self, query=None):
        if query is None:
            query = {}
        count = sum(1 for doc in self.data if self._matches(doc, query))
        return count

class MockDatabase:
    def __init__(self, storage_file: str = MOCK_DB_FILE):
        self.storage_file = storage_file
        self.collections = {}
        self._load_from_disk()

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection(name, db=self)
        return self.collections[name]

    def _load_from_disk(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f, object_hook=_json_deserialize)
                for col_name, docs in raw_data.items():
                    col = MockCollection(col_name, db=self)
                    col.data = docs
                    self.collections[col_name] = col
                logger.info(f"Loaded persistent MockDatabase from {self.storage_file}")
                print(f"SYSTEM LOG: Loaded persistent database state from {self.storage_file}")
            except Exception as e:
                logger.error(f"Failed to load MockDatabase from {self.storage_file}: {e}")

    def save_to_disk(self):
        try:
            raw_data = {}
            for col_name, col in self.collections.items():
                raw_data[col_name] = col.data
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, default=_json_serialize, indent=2)
        except Exception as e:
            logger.error(f"Failed to save MockDatabase to disk: {e}")

# === DB ENGINE SELECTION ===

class Database:
    client = None
    db = None
    is_mock: bool = False

db_instance = Database()

async def connect_to_mongo():
    try:
        # Increase timeout to 5 seconds for remote/cloud MongoDB Atlas connections
        timeout = 5000 if ("+srv" in settings.MONGODB_URL or "mongodb://" in settings.MONGODB_URL) else 2000
        db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=timeout)
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
        logger.warning(f"Could not connect to MongoDB: {e}. Falling back to Persistent File-Backed Mock Database.")
        db_instance.client = None
        db_instance.db = MockDatabase()
        db_instance.is_mock = True
        print(f"SYSTEM LOG: Active Persistent File-Backed Mock Database initialized ({MOCK_DB_FILE}).")


async def close_mongo_connection():
    if db_instance.client and not db_instance.is_mock:
        db_instance.client.close()
        print("MongoDB connection closed")

def get_db():
    if db_instance.db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo first.")
    return db_instance.db
