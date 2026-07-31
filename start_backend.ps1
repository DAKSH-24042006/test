# PowerShell script to run the FastAPI Backend
$env:PYTHONPATH="d:\NFC_FACE_RECOGINITION"
Write-Host "Starting Smart Attendance System FastAPI Backend..." -ForegroundColor Green
& d:\NFC_FACE_RECOGINITION\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
