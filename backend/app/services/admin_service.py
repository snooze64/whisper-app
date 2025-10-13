"""
Admin service for managing administrative operations
"""
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case

from app.models.user import User
from app.models.task import Task
from app.models.processing_history import ProcessingHistory
from app.schemas.processing_history import DashboardStatsResponse, SystemStatusResponse
from app.core.cache import get_cached_data, set_cached_data


class AdminService:
    """Service for admin operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_stats(self) -> DashboardStatsResponse:
        """
        Get dashboard statistics for admin
        Uses Redis cache with 30 second TTL

        Returns:
            DashboardStatsResponse with comprehensive statistics
        """
        # Try to get from cache
        cache_key = "dashboard:stats"
        cached_stats = get_cached_data(cache_key)

        if cached_stats is not None:
            # Return cached data as DashboardStatsResponse
            return DashboardStatsResponse(**cached_stats)

        # Cache miss - fetch from database
        # Get total users count
        users_result = await self.db.execute(select(func.count(User.id)))
        total_users = users_result.scalar() or 0

        # Get total tasks count
        tasks_result = await self.db.execute(select(func.count(Task.id)))
        total_tasks = tasks_result.scalar() or 0

        # Get active tasks count (pending or processing)
        active_tasks_result = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.status.in_(["pending", "processing"])
            )
        )
        active_tasks = active_tasks_result.scalar() or 0

        # Get today's statistics
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Completed tasks today
        completed_today_result = await self.db.execute(
            select(func.count(ProcessingHistory.id)).where(
                and_(
                    ProcessingHistory.created_at >= today_start,
                    ProcessingHistory.success == True
                )
            )
        )
        completed_tasks_today = completed_today_result.scalar() or 0

        # Failed tasks today
        failed_today_result = await self.db.execute(
            select(func.count(ProcessingHistory.id)).where(
                and_(
                    ProcessingHistory.created_at >= today_start,
                    ProcessingHistory.success == False
                )
            )
        )
        failed_tasks_today = failed_today_result.scalar() or 0

        # Average processing time today
        avg_time_result = await self.db.execute(
            select(func.avg(ProcessingHistory.processing_time_seconds)).where(
                ProcessingHistory.created_at >= today_start
            )
        )
        avg_processing_time_today = float(avg_time_result.scalar() or 0)

        # Model usage statistics
        model_usage_result = await self.db.execute(
            select(
                ProcessingHistory.model_name,
                func.count(ProcessingHistory.id).label("count")
            ).group_by(ProcessingHistory.model_name)
        )
        model_usage = {row.model_name: row.count for row in model_usage_result}

        # Format usage statistics
        format_usage_result = await self.db.execute(
            select(
                ProcessingHistory.file_format,
                func.count(ProcessingHistory.id).label("count")
            ).group_by(ProcessingHistory.file_format)
        )
        format_usage = {row.file_format: row.count for row in format_usage_result}

        # Hourly statistics for last 24 hours
        hourly_stats = await self._get_hourly_stats()

        # Create response
        response = DashboardStatsResponse(
            total_users=total_users,
            total_tasks=total_tasks,
            active_tasks=active_tasks,
            completed_tasks_today=completed_tasks_today,
            failed_tasks_today=failed_tasks_today,
            avg_processing_time_today=avg_processing_time_today,
            model_usage=model_usage,
            format_usage=format_usage,
            hourly_stats=hourly_stats
        )

        # Cache the response for 30 seconds
        set_cached_data(cache_key, response.model_dump(), ttl=30)

        return response

    async def _get_hourly_stats(self) -> list[dict]:
        """
        Get hourly task statistics for the last 24 hours

        Returns:
            List of dictionaries with hourly statistics
        """
        # Calculate time 24 hours ago
        time_24h_ago = datetime.utcnow() - timedelta(hours=24)

        # Create hour column
        hour_col = func.date_trunc('hour', ProcessingHistory.created_at).label('hour')

        # Get hourly statistics
        result = await self.db.execute(
            select(
                hour_col,
                func.count(ProcessingHistory.id).label('total'),
                func.sum(
                    case((ProcessingHistory.success == True, 1), else_=0)
                ).label('successful'),
                func.sum(
                    case((ProcessingHistory.success == False, 1), else_=0)
                ).label('failed')
            ).where(
                ProcessingHistory.created_at >= time_24h_ago
            ).group_by(
                hour_col
            ).order_by(
                hour_col
            )
        )

        hourly_stats = []
        for row in result:
            hourly_stats.append({
                "hour": row.hour.isoformat() if row.hour else None,
                "total": int(row.total or 0),
                "successful": int(row.successful or 0),
                "failed": int(row.failed or 0)
            })

        return hourly_stats

    async def get_system_status(self) -> SystemStatusResponse:
        """
        Get current system status including GPU info and task queue

        Returns:
            SystemStatusResponse with system status
        """
        # Try to get GPU information
        gpu_available = False
        gpu_memory_total = None
        gpu_memory_used = None
        gpu_memory_free = None
        gpu_utilization = None

        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)

            # Get memory info
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpu_memory_total = mem_info.total // (1024 ** 2)  # Convert to MB
            gpu_memory_used = mem_info.used // (1024 ** 2)
            gpu_memory_free = mem_info.free // (1024 ** 2)

            # Get utilization
            util_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_utilization = float(util_info.gpu)

            gpu_available = True
            pynvml.nvmlShutdown()
        except Exception:
            # GPU not available or pynvml not installed
            pass

        # Get active workers count (this would require Celery integration)
        # For now, we'll use a placeholder
        active_workers = 0  # TODO: Implement Celery worker count

        # Get pending tasks
        pending_tasks_result = await self.db.execute(
            select(func.count(Task.id)).where(Task.status == "pending")
        )
        pending_tasks = pending_tasks_result.scalar() or 0

        # Get processing tasks
        processing_tasks_result = await self.db.execute(
            select(func.count(Task.id)).where(Task.status == "processing")
        )
        processing_tasks = processing_tasks_result.scalar() or 0

        return SystemStatusResponse(
            gpu_available=gpu_available,
            gpu_memory_total=gpu_memory_total,
            gpu_memory_used=gpu_memory_used,
            gpu_memory_free=gpu_memory_free,
            gpu_utilization=gpu_utilization,
            active_workers=active_workers,
            pending_tasks=pending_tasks,
            processing_tasks=processing_tasks
        )

    async def get_all_users(self, page: int = 1, page_size: int = 50) -> tuple[list[User], int]:
        """
        Get all users with pagination

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (users list, total count)
        """
        # Count total
        count_result = await self.db.execute(select(func.count(User.id)))
        total = count_result.scalar() or 0

        # Get users with pagination
        query = select(User).order_by(User.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        users = result.scalars().all()

        return list(users), total
