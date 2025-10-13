"""
API v1 router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, upload, tasks

api_router = APIRouter()

# Include auth endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include upload endpoints
api_router.include_router(upload.router, tags=["upload"])

# Include task management endpoints
api_router.include_router(tasks.router, tags=["tasks"])

# Future endpoints will be added here
# api_router.include_router(history.router, prefix="/history", tags=["history"])
# api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
