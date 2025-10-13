"""
Task service for managing transcription tasks
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    """Service for task management"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self,
        task_data: TaskCreate,
        file_path: str,
        user_id: int
    ) -> Task:
        """
        Create a new task

        Args:
            task_data: Task creation data
            file_path: Path to uploaded file
            user_id: User ID

        Returns:
            Created task object
        """
        task = Task(
            user_id=user_id,
            filename=task_data.filename,
            file_path=file_path,
            file_size=task_data.file_size,
            file_format=task_data.file_format,
            model_name=task_data.model_name,
            language=task_data.language,
            num_speakers=task_data.num_speakers,
            status="pending",
            progress=0
        )

        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        return task

    async def get_task(
        self,
        task_id: UUID,
        user_id: int,
        is_admin: bool = False
    ) -> Optional[Task]:
        """
        Get task by ID with permission check

        Args:
            task_id: Task ID
            user_id: Current user ID
            is_admin: Whether current user is admin

        Returns:
            Task object or None

        Raises:
            HTTPException: If user doesn't have permission
        """
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        # Permission check: user can only access their own tasks unless admin
        if task.user_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        return task

    async def get_tasks(
        self,
        user_id: int,
        is_admin: bool = False,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Task], int]:
        """
        Get tasks with pagination

        Args:
            user_id: Current user ID
            is_admin: Whether current user is admin
            status: Filter by status (optional)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (tasks list, total count)
        """
        # Build query
        query = select(Task)

        # Filter by user unless admin
        if not is_admin:
            query = query.where(Task.user_id == user_id)

        # Filter by status if provided
        if status:
            query = query.where(Task.status == status)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(Task.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        tasks = result.scalars().all()

        return list(tasks), total

    async def update_task(
        self,
        task_id: UUID,
        task_data: TaskUpdate,
        user_id: int,
        is_admin: bool = False
    ) -> Optional[Task]:
        """
        Update task

        Args:
            task_id: Task ID
            task_data: Update data
            user_id: Current user ID
            is_admin: Whether current user is admin

        Returns:
            Updated task or None

        Raises:
            HTTPException: If user doesn't have permission
        """
        task = await self.get_task(task_id, user_id, is_admin)
        if not task:
            return None

        # Update fields
        update_data = task_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(task, key, value)

        await self.db.commit()
        await self.db.refresh(task)

        return task

    async def delete_task(
        self,
        task_id: UUID,
        user_id: int,
        is_admin: bool = False
    ) -> bool:
        """
        Delete task

        Args:
            task_id: Task ID
            user_id: Current user ID
            is_admin: Whether current user is admin

        Returns:
            True if deleted, False if not found

        Raises:
            HTTPException: If user doesn't have permission
        """
        task = await self.get_task(task_id, user_id, is_admin)
        if not task:
            return False

        await self.db.delete(task)
        await self.db.commit()

        return True

    async def get_task_status(
        self,
        task_id: UUID,
        user_id: int,
        is_admin: bool = False
    ) -> Optional[dict]:
        """
        Get task status (lightweight query)

        Args:
            task_id: Task ID
            user_id: Current user ID
            is_admin: Whether current user is admin

        Returns:
            Dictionary with status info or None
        """
        task = await self.get_task(task_id, user_id, is_admin)
        if not task:
            return None

        return {
            "id": task.id,
            "status": task.status,
            "progress": task.progress,
            "error_message": task.error_message
        }
