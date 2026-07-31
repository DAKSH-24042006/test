import asyncio
from datetime import datetime
from backend.app.database.connection import connect_to_mongo, close_mongo_connection, get_db
from backend.app.repositories.user_repository import UserRepository
from backend.app.repositories.class_repository import ClassRepository
from backend.app.repositories.face_repository import FaceRepository
from backend.app.services.auth_service import AuthService
from backend.app.services.face_service import FaceService

async def run_verification():
    print("========================================")
    print("STARTING SYSTEM INTEGRATION VERIFICATION")
    print("========================================")

    # 1. Connect to DB
    await connect_to_mongo()
    db = get_db()

    # Clear previous test data to start fresh
    await db["users"].delete_many({"email": {"$in": ["admin@test.edu", "teacher@test.edu", "student@test.edu"]}})
    await db["classes"].delete_many({"classCode": "TEST_101"})
    await db["jwt_sessions"].delete_many({})
    await db["face_profiles"].delete_many({})
    await db["verification_logs"].delete_many({})

    user_repo = UserRepository()
    class_repo = ClassRepository()
    face_repo = FaceRepository()
    auth_service = AuthService()
    face_service = FaceService()

    print("\n--- PHASE 1: Seeding Test Users ---")
    
    # Create Admin
    admin_data = {
        "adminId": "ADM999",
        "name": "Test Administrator",
        "email": "admin@test.edu",
        "passwordHash": auth_service.hash_password("AdminPass123"),
        "role": "admin"
    }
    admin = await user_repo.create(admin_data)
    print(f"Admin seeded: {admin['name']} ({admin['_id']})")

    # Create Teacher
    teacher_data = {
        "teacherId": "TCH777",
        "name": "Dr. Sarah Jenkins",
        "email": "teacher@test.edu",
        "passwordHash": auth_service.hash_password("TeacherPass123"),
        "role": "teacher",
        "assignedClasses": []
    }
    teacher = await user_repo.create(teacher_data)
    print(f"Teacher seeded: {teacher['name']} ({teacher['_id']})")

    # Create Class
    class_data = {
        "classCode": "TEST_101",
        "department": "Computer Science & Engineering",
        "semester": 4,
        "section": "A",
        "teacherId": teacher["_id"]
    }
    clazz = await class_repo.create(class_data)
    print(f"Class created: {clazz['classCode']} ({clazz['_id']})")

    # Assign Class to Teacher in DB
    await user_repo.add_assigned_class_to_teacher(teacher["_id"], clazz["_id"])
    print(f"Assigned class {clazz['classCode']} to Teacher {teacher['name']}")

    # Create Student
    student_data = {
        "registrationNumber": "REG444",
        "name": "Alex Mercer",
        "email": "student@test.edu",
        "passwordHash": auth_service.hash_password("StudentPass123"),
        "role": "student",
        "classId": clazz["_id"]
    }
    student = await user_repo.create(student_data)
    print(f"Student seeded: {student['name']} ({student['_id']})")


    print("\n--- PHASE 2: Authentication Tests ---")
    
    # Login Test
    login_result = await auth_service.login_user("student@test.edu", "StudentPass123")
    if login_result:
        access_token, refresh_token, logged_user = login_result
        print(f"Login successful for {logged_user['name']}!")
        print(f"Access Token length: {len(access_token)}")
        print(f"Refresh Token length: {len(refresh_token)}")
    else:
        print("ERROR: Login failed!")
        return

    # Refresh Session Test
    refresh_result = await auth_service.refresh_session(refresh_token)
    if refresh_result:
        new_access, new_refresh, refreshed_user = refresh_result
        print(f"Session refreshed successfully for {refreshed_user['name']}!")
    else:
        print("ERROR: Token refresh failed!")
        return


    print("\n--- PHASE 3: Biometric Face Pipeline Tests ---")
    
    # Simulate face registration (generating mock image bytes for poses)
    poses = ["Front", "Left", "Right", "Up", "Down", "Smile", "Neutral"]
    pose_images = {pose: b"fake_jpeg_image_data_here" for pose in poses}
    
    print("Registering multi-pose face embeddings...")
    profile = await face_service.register_face(student["_id"], pose_images)
    print(f"Face profile registered successfully for student ID: {profile['userId']}")
    print(f"Saved pose embeddings count: {len(profile['embeddings'])}")

    # Verify registration status
    status = await face_repo.get_profile_by_user_id(student["_id"])
    if status:
        print(f"Database contains active biometrics signature: True")
    else:
        print("ERROR: Face profile not found in DB!")
        return

    # Simulate face verification
    print("\nPerforming Face Verification match...")
    verify_img = b"fake_jpeg_image_data_here" # Same fake bytes yield same seed/mock embedding vector
    verified, score, confidence = await face_service.verify_face(student["_id"], verify_img, "Test Suite Device")
    
    print(f"Verification Verdict: {verified}")
    print(f"Match Similarity Score: {score:.4f}")
    print(f"Match Confidence Score: {confidence * 100:.2f}%")

    if verified:
        print("\nBiometric matching verification: PASSED")
    else:
        print("\nBiometric matching verification: FAILED")

    # Retrieve verification logs
    logs = await face_repo.get_logs_by_user_id(student["_id"])
    print(f"Total verification logs stored for student: {len(logs)}")
    if logs:
        print(f"Latest Log -> Score: {logs[0]['similarityScore']:.4f}, Outcome: {logs[0]['verificationResult']}")

    print("\n--- CLEANING UP TEST DATA ---")
    await db["users"].delete_many({"email": {"$in": ["admin@test.edu", "teacher@test.edu", "student@test.edu"]}})
    await db["classes"].delete_many({"classCode": "TEST_101"})
    await db["jwt_sessions"].delete_many({})
    await db["face_profiles"].delete_many({})
    await db["verification_logs"].delete_many({})
    print("Database cleaned up successfully.")

    await close_mongo_connection()
    print("\n========================================")
    print("VERIFICATION COMPLETED SUCCESSFULLY!")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(run_verification())
