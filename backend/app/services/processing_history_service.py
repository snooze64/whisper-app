"""
ProcessingHistory service for managing processing history records
"""
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from fastapi import HTTPException

from app.models.processing_history import ProcessingHistory
from app.models.task import Task
from app.schemas.processing_history import ProcessingHistoryStatsResponse


class ProcessingHistoryService:
    """Service for processing history management"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_history(
        self,
        task_id: str,
        user_id: int,
        processing_time_seconds: int,
        gpu_memory_used_mb: Optional[int],
        model_name: str,
        file_format: str,
        file_size_mb: Decimal,
        success: bool,
        error_type: Optional[str] = None
    ) -> ProcessingHistory:
        """
        Create a new processing history record

        Args:
            task_id: Task UUID
            user_id: User ID
            processing_time_seconds: Processing time in seconds
            gpu_memory_used_mb: GPU memory used in MB (optional)
            model_name: Whisper model name used
            file_format: File format
            file_size_mb: File size in MB
            success: Whether processing was successful
            error_type: Error type if failed (optional)

        Returns:
            Created ProcessingHistory object
        """
        history = ProcessingHistory(
            task_id=task_id,
            user_id=user_id,
            processing_time_seconds=processing_time_seconds,
            gpu_memory_used_mb=gpu_memory_used_mb,
            model_name=model_name,
            file_format=file_format,
            file_size_mb=file_size_mb,
            success=success,
            error_type=error_type
        )

        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)

        return history

    async def get_history(
        self,
        history_id: int,
        user_id: int,
        is_admin: bool = False
    ) -> Optional[ProcessingHistory]:
        """
        Get processing history by ID with permission check

        Args:
            history_id: History ID
            user_id: Current user ID
            is_admin: Whether current user is admin

        Returns:
            ProcessingHistory object or None

        Raises:
            HTTPException: If user doesn't have permission
        """
        result = await self.db.execute(
            select(ProcessingHistory).where(ProcessingHistory.id == history_id)
        )
        history = result.scalar_one_or_none()

        if not history:
            return None

        # Permission check: user can only access their own history unless admin
        if history.user_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        return history

    async def get_history_list(
        self,
        user_id: int,
        is_admin: bool = False,
        success: Optional[bool] = None,
        model_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[ProcessingHistory], int]:
        """
        Get processing history with pagination

        Args:
            user_id: Current user ID
            is_admin: Whether current user is admin
            success: Filter by success status (optional)
            model_name: Filter by model name (optional)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (history list, total count)
        """
        # Build query
        query = select(ProcessingHistory)

        # Filter by user unless admin
        if not is_admin:
            query = query.where(ProcessingHistory.user_id == user_id)

        # Filter by success if provided
        if success is not None:
            query = query.where(ProcessingHistory.success == success)

        # Filter by model_name if provided
        if model_name:
            query = query.where(ProcessingHistory.model_name == model_name)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(ProcessingHistory.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        history_list = result.scalars().all()

        return list(history_list), total

    async def get_user_statistics(
        self,
        user_id: int,
        is_admin: bool = False,
        days: int = 30
    ) -> ProcessingHistoryStatsResponse:
        """
        Get user processing statistics

        Args:
            user_id: User ID (only for non-admin users)
            is_admin: Whether to get statistics for all users
            days: Number of days to look back (default 30)

        Returns:
            ProcessingHistoryStatsResponse with statistics
        """
        # Build base query
        query = select(ProcessingHistory)

        # Filter by user unless admin
        if not is_admin:
            query = query.where(ProcessingHistory.user_id == user_id)

        # Filter by date range
        if days > 0:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(ProcessingHistory.created_at >= cutoff_date)

        # Get all records for statistics
        result = await self.db.execute(query)
        records = result.scalars().all()

        total_tasks = len(records)
        successful_tasks = sum(1 for r in records if r.success)
        failed_tasks = total_tasks - successful_tasks
        success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

        total_processing_time = sum(r.processing_time_seconds for r in records)
        avg_processing_time = (total_processing_time / total_tasks) if total_tasks > 0 else 0.0

        gpu_memories = [r.gpu_memory_used_mb for r in records if r.gpu_memory_used_mb is not None]
        avg_gpu_memory = (sum(gpu_memories) / len(gpu_memories)) if gpu_memories else None

        total_file_size = sum(float(r.file_size_mb) for r in records)

        return ProcessingHistoryStatsResponse(
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            success_rate=success_rate,
            avg_processing_time=avg_processing_time,
            total_processing_time=total_processing_time,
            avg_gpu_memory=avg_gpu_memory,
            total_file_size=total_file_size
        )
