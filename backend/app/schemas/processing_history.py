"""
ProcessingHistory schemas for request/response validation
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from uuid import UUID


class ProcessingHistoryBase(BaseModel):
    """Base processing history schema"""
    model_config = {"protected_namespaces": ()}

    processing_time_seconds: int = Field(..., description="Processing time in seconds")
    gpu_memory_used_mb: Optional[int] = Field(None, description="GPU memory used in MB")
    model_name: str = Field(..., description="Whisper model name used")
    file_format: str = Field(..., description="File format (mp3, wav, mp4)")
    file_size_mb: Decimal = Field(..., description="File size in MB")
    success: bool = Field(..., description="Whether processing was successful")
    error_type: Optional[str] = Field(None, description="Error type if failed")


class ProcessingHistoryResponse(ProcessingHistoryBase):
    """Schema for processing history response"""
    id: int
    task_id: UUID
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProcessingHistoryListResponse(BaseModel):
    """Schema for processing history list response"""
    history: list[ProcessingHistoryResponse]
    total: int
    page: int
    page_size: int


class ProcessingHistoryStatsResponse(BaseModel):
    """Schema for processing history statistics"""
    total_tasks: int = Field(..., description="Total number of tasks processed")
    successful_tasks: int = Field(..., description="Number of successful tasks")
    failed_tasks: int = Field(..., description="Number of failed tasks")
    success_rate: float = Field(..., description="Success rate as percentage")
    avg_processing_time: float = Field(..., description="Average processing time in seconds")
    total_processing_time: int = Field(..., description="Total processing time in seconds")
    avg_gpu_memory: Optional[float] = Field(None, description="Average GPU memory used in MB")
    total_file_size: float = Field(..., description="Total file size processed in MB")


class DashboardStatsResponse(BaseModel):
    """Schema for admin dashboard statistics"""
    model_config = {"protected_namespaces": ()}

    total_users: int
    total_tasks: int
    active_tasks: int
    completed_tasks_today: int
    failed_tasks_today: int
    avg_processing_time_today: float
    model_usage: dict[str, int] = Field(..., description="Task count by model")
    format_usage: dict[str, int] = Field(..., description="Task count by format")
    hourly_stats: list[dict] = Field(..., description="Hourly task statistics for last 24 hours")


class SystemStatusResponse(BaseModel):
    """Schema for system status"""
    gpu_available: bool = Field(..., description="Whether GPU is available")
    gpu_memory_total: Optional[int] = Field(None, description="Total GPU memory in MB")
    gpu_memory_used: Optional[int] = Field(None, description="Used GPU memory in MB")
    gpu_memory_free: Optional[int] = Field(None, description="Free GPU memory in MB")
    gpu_utilization: Optional[float] = Field(None, description="GPU utilization percentage")
    active_workers: int = Field(..., description="Number of active Celery workers")
    pending_tasks: int = Field(..., description="Number of pending tasks in queue")
    processing_tasks: int = Field(..., description="Number of currently processing tasks")
