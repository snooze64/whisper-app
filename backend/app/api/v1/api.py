"""
API v1 router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth

api_router = APIRouter()

# Include auth endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Future endpoints will be added here
# api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
# api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
# api_router.include_router(history.router, prefix="/history", tags=["history"])
# api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
