"""
Task schemas for request/response validation
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from uuid import UUID


class TaskBase(BaseModel):
    """Base task schema"""
    model_config = {"protected_namespaces": ()}

    model_name: str = Field(..., description="Whisper model name (large-v3, large-v3-turbo)")
    language: str = Field(default="ja", description="Language code (ja, en, zh, etc.)")
    num_speakers: Optional[int] = Field(None, description="Number of speakers for diarization")

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        allowed_models = ["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"]
        if v not in allowed_models:
            raise ValueError(f"Model must be one of {allowed_models}")
        return v

    @field_validator("num_speakers")
    @classmethod
    def validate_num_speakers(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Number of speakers must be between 1 and 10")
        return v


class TaskCreate(TaskBase):
    """Schema for creating a new task"""
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_format: str = Field(..., description="File format (mp3, wav, mp4)")


class TaskUpdate(BaseModel):
    """Schema for updating task status"""
    status: Optional[str] = None
    progress: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class TaskResponse(TaskBase):
    """Schema for task response"""
    id: UUID
    user_id: int
    filename: str
    file_size: int
    file_format: str
    status: str
    progress: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Schema for task list response"""
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int


class TaskStatusResponse(BaseModel):
    """Schema for task status response"""
    id: UUID
    status: str
    progress: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
