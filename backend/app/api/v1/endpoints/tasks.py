"""
Task management API endpoints
"""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.task import TaskResponse, TaskListResponse, TaskStatusResponse
from app.services.task_service import TaskService
from app.services.file_service import FileService

router = APIRouter()


@router.get("/tasks", response_model=TaskListResponse)
async def get_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get task list

    - **status**: Filter by status (pending, processing, completed, failed)
    - **page**: Page number (1-indexed)
    - **page_size**: Number of items per page (max 100)

    Returns paginated task list. Regular users see only their own tasks,
    admins see all tasks.
    """
    task_service = TaskService(db)
    tasks, total = await task_service.get_tasks(
        user_id=current_user.id,
        is_admin=current_user.is_admin,
        status=status,
        page=page,
        page_size=page_size
    )

    return TaskListResponse(
        tasks=tasks,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get task details by ID

    Returns full task information. Users can only access their own tasks
    unless they are admins.
    """
    task_service = TaskService(db)
    task = await task_service.get_task(
        task_id=task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get task status (lightweight endpoint for polling)

    Returns only status, progress, and error message.
    Useful for frontend polling to update UI.
    """
    task_service = TaskService(db)
    status = await task_service.get_task_status(
        task_id=task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )

    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return status


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete task and associated files

    Users can only delete their own tasks unless they are admins.
    This will also delete the uploaded file and any generated results.
    """
    task_service = TaskService(db)

    # Get task to delete file
    task = await task_service.get_task(
        task_id=task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Delete file from storage
    FileService.delete_file(task.file_path)

    # Delete task from database
    deleted = await task_service.delete_task(
        task_id=task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")

    return None
