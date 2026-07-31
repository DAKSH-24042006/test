from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database.connection import connect_to_mongo, close_mongo_connection
from backend.app.routes import auth_routes, admin_routes, teacher_routes, student_routes, face_routes
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.auth_service import AuthService
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(
    title="Smart Attendance System API",
    description="API backend for Version 1 of the Enterprise Smart Attendance System.",
    version="1.0.0"
)

# Configure CORS for Flutter client communication (allows all hosts for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes under /api/v1
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(admin_routes.router, prefix="/api/v1")
app.include_router(teacher_routes.router, prefix="/api/v1")
app.include_router(student_routes.router, prefix="/api/v1")
app.include_router(face_routes.router, prefix="/api/v1")

# Mount Static Files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
async def startup_event():
    # Connect to MongoDB
    await connect_to_mongo()
    
    # Auto-seed Default Administrator if no admin exists
    try:
        user_repo = UserRepository()
        auth_service = AuthService()
        admins = await user_repo.list_by_role("admin")
        if not admins:
            print("No admin user found. Seeding default system administrator...")
            admin_data = {
                "adminId": "ADM001",
                "name": "System Administrator",
                "email": "admin@smart.edu",
                "passwordHash": auth_service.hash_password("AdminPassword123"),
                "role": "admin"
            }
            await user_repo.create(admin_data)
            print("Default admin created: admin@smart.edu / AdminPassword123")
        
        # Auto-seed Default Student if no student exists
        students = await user_repo.list_by_role("student")
        if not students:
            print("No student user found. Seeding default student profile...")
            student_data = {
                "registrationNumber": "REG001",
                "name": "Alex Mercer",
                "email": "student@smart.edu",
                "passwordHash": auth_service.hash_password("StudentPassword123"),
                "role": "student",
                "registrationApprovalStatus": "none"
            }
            await user_repo.create(student_data)
            print("Default student created: student@smart.edu / StudentPassword123")
            
    except Exception as e:
        print(f"Error during system seeding: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")
