"""
Admin API endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_admin
from app.models.user import User
from app.services.admin_service import AdminService
from app.services.task_service import TaskService
from app.services.processing_history_service import ProcessingHistoryService
from app.schemas.user import User as UserSchema
from app.schemas.task import TaskListResponse, TaskResponse
from app.schemas.processing_history import (
    DashboardStatsResponse,
    SystemStatusResponse,
    ProcessingHistoryStatsResponse,
)

router = APIRouter()


@router.get("/admin/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get admin dashboard statistics

    Returns comprehensive statistics for the admin dashboard including:
    - Total users, tasks, active tasks
    - Today's completed/failed tasks
    - Average processing time
    - Model and format usage statistics
    - Hourly statistics for last 24 hours

    **Admin only**: This endpoint requires admin privileges.
    """
    service = AdminService(db)
    stats = await service.get_dashboard_stats()

    return stats


@router.get("/admin/system-status", response_model=SystemStatusResponse)
async def get_system_status(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get system status

    Returns current system status including:
    - GPU availability and memory usage
    - GPU utilization percentage
    - Active Celery workers
    - Pending and processing task counts

    **Admin only**: This endpoint requires admin privileges.
    """
    service = AdminService(db)
    status = await service.get_system_status()

    return status


@router.get("/admin/users", response_model=List[UserSchema])
async def get_all_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all users

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)

    Returns paginated list of all users.

    **Admin only**: This endpoint requires admin privileges.
    """
    service = AdminService(db)
    users, total = await service.get_all_users(page=page, page_size=page_size)

    return [UserSchema.model_validate(u) for u in users]


@router.get("/admin/tasks", response_model=TaskListResponse)
async def get_all_tasks(
    status: str = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all tasks from all users

    - **status**: Filter by status (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)

    Returns paginated list of all tasks from all users.

    **Admin only**: This endpoint requires admin privileges.
    """
    service = TaskService(db)
    tasks, total = await service.get_tasks(
        user_id=current_user.id,
        is_admin=True,  # Admin can see all tasks
        status=status,
        page=page,
        page_size=page_size
    )

    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/admin/stats", response_model=ProcessingHistoryStatsResponse)
async def get_all_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall processing statistics for all users

    - **days**: Number of days to look back (default: 30, max: 365)

    Returns processing statistics for all users.

    **Admin only**: This endpoint requires admin privileges.
    """
    service = ProcessingHistoryService(db)
    stats = await service.get_user_statistics(
        user_id=current_user.id,
        is_admin=True,  # Get stats for all users
        days=days
    )

    return stats
