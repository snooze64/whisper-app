"""
Pydantic schemas
"""
from app.schemas.user import User, UserCreate, UserUpdate, UserInDB
from app.schemas.auth import LoginRequest, TokenResponse, TokenRefreshRequest, TokenData
from app.schemas.transcription import (
    TranscriptionSegment,
    TranscriptionBase,
    TranscriptionCreate,
    TranscriptionUpdate,
    TranscriptionResponse,
    SegmentUpdateRequest,
)
from app.schemas.processing_history import (
    ProcessingHistoryResponse,
    ProcessingHistoryListResponse,
    ProcessingHistoryStatsResponse,
    DashboardStatsResponse,
    SystemStatusResponse,
)

__all__ = [
    "User",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "LoginRequest",
    "TokenResponse",
    "TokenRefreshRequest",
    "TokenData",
    "TranscriptionSegment",
    "TranscriptionBase",
    "TranscriptionCreate",
    "TranscriptionUpdate",
    "TranscriptionResponse",
    "SegmentUpdateRequest",
    "ProcessingHistoryResponse",
    "ProcessingHistoryListResponse",
    "ProcessingHistoryStatsResponse",
    "DashboardStatsResponse",
    "SystemStatusResponse",
]
