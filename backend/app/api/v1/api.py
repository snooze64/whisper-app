"""
API v1 router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, upload, tasks, transcriptions, history, admin

api_router = APIRouter()

# Include auth endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include upload endpoints
api_router.include_router(upload.router, tags=["upload"])

# Include task management endpoints
api_router.include_router(tasks.router, tags=["tasks"])

# Include transcription endpoints
api_router.include_router(transcriptions.router, tags=["transcriptions"])

# Include processing history endpoints
api_router.include_router(history.router, tags=["history"])

# Include admin endpoints
api_router.include_router(admin.router, tags=["admin"])
