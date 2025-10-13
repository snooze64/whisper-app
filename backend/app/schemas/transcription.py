"""
Transcription Pydantic schemas
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, UUID4


class TranscriptionSegment(BaseModel):
    """Schema for a single transcription segment"""
    id: int
    start: float
    end: float
    text: str
    speaker_id: Optional[int] = None
    speaker_label: Optional[str] = None
    confidence: Optional[float] = None
    avg_logprob: Optional[float] = None
    no_speech_prob: Optional[float] = None
    words: Optional[List[Dict[str, Any]]] = None


class TranscriptionBase(BaseModel):
    """Base Transcription schema"""
    transcription_text: str
    segments: List[Dict[str, Any]]
    word_count: Optional[int] = None


class TranscriptionCreate(TranscriptionBase):
    """Schema for creating a transcription"""
    task_id: UUID4


class TranscriptionUpdate(BaseModel):
    """Schema for updating a transcription"""
    transcription_text: Optional[str] = None
    segments: Optional[List[Dict[str, Any]]] = None
    word_count: Optional[int] = None


class TranscriptionResponse(TranscriptionBase):
    """Schema for transcription response"""
    id: int
    task_id: UUID4
    subtitle_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SegmentUpdateRequest(BaseModel):
    """Schema for updating a single segment"""
    segment_id: int
    text: Optional[str] = None
    start: Optional[float] = None
    end: Optional[float] = None
    speaker_label: Optional[str] = None
