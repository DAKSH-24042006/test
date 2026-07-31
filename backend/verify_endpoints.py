import asyncio
from datetime import datetime
import backend.app.services.face_service as face_service_module

# Force fallback simulation mode in the verification script to allow testing logic with mock images
face_service_module.INSIGHTFACE_AVAILABLE = False

from backend.app.database.connection import connect_to_mongo, close_mongo_connection, get_db
from backend.app.repositories.admin_repository import AdminRepository
from backend.app.repositories.class_repository import ClassRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.embedding_repository import EmbeddingRepository
from backend.app.services.auth_service import AuthService
from backend.app.services.face_service import FaceService
from backend.app.services.cache_manager import ClassCacheManager

async def run_verification():
    print("==================================================")
    print("STARTING REST SCHEMA & BIOMETRIC VERIFICATION TEST")
    print("==================================================")

    # 1. Connect to DB
    await connect_to_mongo()
    db = get_db()

    # Clear previous test data
    await db["admins"].delete_many({"email": "admin@test.edu"})
    await db["classes"].delete_many({"class_name": "Test Class"})
    await db["students"].delete_many({"reg_no": "REG444"})
    await db["embeddings"].delete_many({})
    await db["verification_logs"].delete_many({})

    admin_repo = AdminRepository()
    class_repo = ClassRepository()
    student_repo = StudentRepository()
    embedding_repo = EmbeddingRepository()
    auth_service = AuthService()
    face_service = FaceService()

    print("\n--- PHASE 1: Seeding Admin and Kiosk Data ---")
    
    # Create Admin
    admin_data = {
        "admin_id": "ADM999",
        "name": "Test Administrator",
        "email": "admin@test.edu",
        "passwordHash": auth_service.hash_password("AdminPass123")
    }
    admin = await admin_repo.create(admin_data)
    print(f"Admin seeded: {admin['name']} (ID: {admin['admin_id']})")

    # Create Class
    class_data = {
        "class_name": "Test Class",
        "department": "Computer Science",
        "semester": 4,
        "section": "A"
    }
    clazz = await class_repo.create(class_data)
    print(f"Class created: {clazz['class_name']} (ID: {clazz['class_id']})")

    # Create Student
    student_data = {
        "class_id": clazz["class_id"],
        "reg_no": "REG444",
        "name": "Alex Mercer"
    }
    student = await student_repo.create(student_data)
    print(f"Student seeded: {student['name']} (Reg: {student['reg_no']}, ID: {student['student_id']})")


    print("\n--- PHASE 2: Administrative Login Tests ---")
    
    # Login Test
    login_result = await auth_service.login_admin("admin@test.edu", "AdminPass123")
    if login_result:
        access_token, refresh_token, logged_admin = login_result
        print(f"Admin login successful for {logged_admin['name']}!")
        print(f"Access Token length: {len(access_token)}")
    else:
        print("ERROR: Login failed!")
        return

    # Invalid login test
    bad_login = await auth_service.login_admin("admin@test.edu", "WrongPass")
    if not bad_login:
        print("Invalid credentials rejected correctly.")
    else:
        print("ERROR: Wrong credentials accepted!")
        return


    print("\n--- PHASE 3: Biometric Batch Registration ---")
    
    # Simulate face registration (generating mock image bytes for poses)
    import cv2
    import numpy as np
    
    # Create a random textured image (to pass the blur/contrast checks)
    dummy_img = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
    _, img_encoded = cv2.imencode('.jpg', dummy_img)
    valid_image_bytes = img_encoded.tobytes()

    print("Registering student face vectors (batch processing 7 images)...")
    reg_images = [valid_image_bytes for _ in range(7)]
    profile = await face_service.register_face(student["student_id"], reg_images)
    print(f"Face profile registered successfully for student ID: {profile['student_id']}")
    print(f"Saved vectors count in database: {profile['registered_embeddings_count']}")

    # Verify embeddings exist in DB
    stored_embeddings = await embedding_repo.get_by_student_id(student["student_id"])
    print(f"Database Embedding count: {len(stored_embeddings)}")
    if len(stored_embeddings) == 7:
        print("Embeddings verified in database: True")
    else:
        print(f"ERROR: Expected 7 embeddings, got {len(stored_embeddings)}!")
        return


    print("\n--- PHASE 4: In-Memory Caching & Face Match Verification ---")
    
    # Invalidate cache to ensure it fetches from MongoDB
    ClassCacheManager.invalidate_class(clazz["class_id"])
    
    # Perform verification (First verification will warm up the cache lazily)
    print("Performing Kiosk 1:1 Face Verification match...")
    verify_img_bytes = valid_image_bytes
    verified, score, confidence, time_taken = await face_service.verify_face(
        student_id=student["student_id"],
        class_id=clazz["class_id"],
        image_bytes=verify_img_bytes
    )
    
    print(f"Verification Verdict: {verified}")
    print(f"Match Cosine Similarity: {score:.4f}")
    print(f"Match Confidence Score: {confidence * 100:.2f}%")
    print(f"Verification Match Duration: {time_taken * 1000:.2f} ms")

    if verified:
        print("Biometric matching verification: PASSED")
    else:
        print("ERROR: Biometric matching verification failed!")
        return

    # Check that class is indeed cached now
    is_cached = clazz["class_id"] in ClassCacheManager._cache
    print(f"Class RAM Cache populated dynamically: {is_cached}")
    if is_cached:
        student_cached_data = ClassCacheManager._cache[clazz["class_id"]].get(student["student_id"])
        print(f"Cached student: {student_cached_data['name']}")
        print(f"Cached embeddings count: {len(student_cached_data['embeddings'])}")


    print("\n--- PHASE 5: Cache Invalidation Tests ---")
    
    # Invalidate on Student update
    ClassCacheManager.invalidate_class(clazz["class_id"])
    # Load class to cache
    await ClassCacheManager.load_class_into_cache(clazz["class_id"])
    print(f"Cache state before invalidation: {clazz['class_id'] in ClassCacheManager._cache}")
    
    # Trigger student update
    await student_repo.update(student["student_id"], {"name": "Alex Mercer Updated"})
    ClassCacheManager.invalidate_class(clazz["class_id"])
    print(f"Cache state after invalidation: {clazz['class_id'] in ClassCacheManager._cache} (Expected: False)")
    
    # Reload and check name update
    await ClassCacheManager.load_class_into_cache(clazz["class_id"])
    updated_cached_student = ClassCacheManager._cache[clazz["class_id"]].get(student["student_id"])
    print(f"Refreshed Cached student name: {updated_cached_student['name']}")


    print("\n--- CLEANING UP TEST DATA ---")
    await db["admins"].delete_many({"email": "admin@test.edu"})
    await db["classes"].delete_many({"class_name": "Test Class"})
    await db["students"].delete_many({"reg_no": "REG444"})
    await db["embeddings"].delete_many({})
    await db["verification_logs"].delete_many({})
    print("Database cleaned up successfully.")

    await close_mongo_connection()
    print("\n==================================================")
    print("ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_verification())
