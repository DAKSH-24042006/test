import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from backend.app.database.connection import connect_to_mongo, close_mongo_connection
from backend.app.routes import auth_routes, admin_routes, student_routes
from backend.app.repositories.admin_repository import AdminRepository
from backend.app.repositories.class_repository import ClassRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.services.auth_service import AuthService

app = FastAPI(
    title="Biometric Face Registration & Verification API",
    description="REST API backend for Face Registration (Admin) and Face Verification (Student kiosk).",
    version="1.0.0"
)

# Configure CORS for Flutter client communication
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
app.include_router(student_routes.router, prefix="/api/v1")

# Mount Static Files for Admin Panel
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
        admin_repo = AdminRepository()
        class_repo = ClassRepository()
        student_repo = StudentRepository()
        auth_service = AuthService()
        
        admins = await admin_repo.list_all()
        if not admins:
            print("No admin user found. Seeding default system administrator...")
            admin_data = {
                "admin_id": "ADM001",
                "name": "System Administrator",
                "email": "admin@smart.edu",
                "passwordHash": auth_service.hash_password("AdminPassword123")
            }
            await admin_repo.create(admin_data)
            print("Default admin seeded: admin@smart.edu / AdminPassword123")
        
        # Auto-seed Default Class & Student if none exist
        classes = await class_repo.list_all()
        if not classes:
            print("No classes found. Seeding default class...")
            class_data = {
                "class_name": "BTech CSE A",
                "department": "CSE",
                "semester": 3,
                "section": "A"
            }
            c_res = await class_repo.create(class_data)
            print(f"Default class seeded: {class_data['class_name']} (ID: {c_res['class_id']})")
            
            students = await student_repo.list_all()
            if not students:
                print("No students found. Seeding default student...")
                student_data = {
                    "class_id": c_res["class_id"],
                    "reg_no": "REG001",
                    "name": "Alex Mercer"
                }
                await student_repo.create(student_data)
                print(f"Default student seeded: {student_data['name']} (Reg: {student_data['reg_no']})")
                
    except Exception as e:
        print(f"Error during system seeding: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")
