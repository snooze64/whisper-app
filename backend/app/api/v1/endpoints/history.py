"""
Processing history API endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.processing_history_service import ProcessingHistoryService
from app.schemas.processing_history import (
    ProcessingHistoryResponse,
    ProcessingHistoryListResponse,
    ProcessingHistoryStatsResponse,
)

router = APIRouter()


@router.get("/history", response_model=ProcessingHistoryListResponse)
async def get_processing_history_list(
    success: Optional[bool] = Query(None, description="Filter by success status"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get processing history list

    - **success**: Filter by success status (optional)
    - **model_name**: Filter by model name (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)

    Returns paginated processing history list.
    Users see only their own history unless they are admins.
    """
    service = ProcessingHistoryService(db)
    history_list, total = await service.get_history_list(
        user_id=current_user.id,
        is_admin=current_user.is_admin,
        success=success,
        model_name=model_name,
        page=page,
        page_size=page_size
    )

    return ProcessingHistoryListResponse(
        history=[ProcessingHistoryResponse.model_validate(h) for h in history_list],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/history/{history_id}", response_model=ProcessingHistoryResponse)
async def get_processing_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get processing history detail by ID

    - **history_id**: Processing history ID

    Returns processing history detail.
    Users can only access their own history unless they are admins.
    """
    service = ProcessingHistoryService(db)
    history = await service.get_history(
        history_id=history_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )

    if not history:
        raise HTTPException(status_code=404, detail="Processing history not found")

    return ProcessingHistoryResponse.model_validate(history)


@router.get("/history/stats/me", response_model=ProcessingHistoryStatsResponse)
async def get_my_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's processing statistics

    - **days**: Number of days to look back (default: 30, max: 365)

    Returns processing statistics for the current user.
    """
    service = ProcessingHistoryService(db)
    stats = await service.get_user_statistics(
        user_id=current_user.id,
        is_admin=False,  # Always use user-specific stats for this endpoint
        days=days
    )

    return stats
