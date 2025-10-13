"""
Transcription service for managing transcription results
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.transcription import Transcription
from app.models.task import Task
from app.schemas.transcription import TranscriptionUpdate


class TranscriptionService:
    """Service for transcription management"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_transcription_by_task_id(
        self,
        task_id: UUID,
        user_id: int,
        is_admin: bool = False
    ) -> Optional[Transcription]:
        """
        Get transcription by task ID with permission check

        Args:
            task_id: Task ID
            user_id: Current user ID
            is_admin: Whether current user is admin

        Returns:
            Transcription object or None

        Raises:
            HTTPException: If user doesn't have permission or task not found
        """
        # First check task exists and user has permission
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Permission check: user can only access their own tasks unless admin
        if task.user_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get transcription
        result = await self.db.execute(
            select(Transcription).where(Transcription.task_id == task_id)
        )
        transcription = result.scalar_one_or_none()

        if not transcription:
            raise HTTPException(status_code=404, detail="Transcription not found")

        return transcription

    async def update_transcription(
        self,
        task_id: UUID,
        transcription_data: TranscriptionUpdate,
        user_id: int,
        is_admin: bool = False
    ) -> Transcription:
        """
        Update transcription

        Args:
            task_id: Task ID
            transcription_data: Update data
            user_id: Current user ID
            is_admin: Whether current user is admin

        Returns:
            Updated transcription

        Raises:
            HTTPException: If user doesn't have permission or not found
        """
        # Get transcription with permission check
        transcription = await self.get_transcription_by_task_id(
            task_id, user_id, is_admin
        )

        # Update fields
        update_data = transcription_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(transcription, key, value)

        await self.db.commit()
        await self.db.refresh(transcription)

        return transcription

    async def update_segment(
        self,
        task_id: UUID,
        segment_id: int,
        text: Optional[str] = None,
        start: Optional[float] = None,
        end: Optional[float] = None,
        speaker_label: Optional[str] = None,
        user_id: int = None,
        is_admin: bool = False
    ) -> Transcription:
        """
        Update a single segment in the transcription

        Args:
            task_id: Task ID
            segment_id: Segment ID to update
            text: New text (optional)
            start: New start time (optional)
            end: New end time (optional)
            speaker_label: New speaker label (optional)
            user_id: Current user ID
            is_admin: Whether current user is admin

        Returns:
            Updated transcription

        Raises:
            HTTPException: If user doesn't have permission, not found, or invalid segment
        """
        # Get transcription with permission check
        transcription = await self.get_transcription_by_task_id(
            task_id, user_id, is_admin
        )

        # Find and update the segment
        segments = transcription.segments
        segment_found = False

        for segment in segments:
            if segment.get("id") == segment_id:
                segment_found = True
                if text is not None:
                    segment["text"] = text
                if start is not None:
                    segment["start"] = start
                if end is not None:
                    segment["end"] = end
                if speaker_label is not None:
                    segment["speaker_label"] = speaker_label
                break

        if not segment_found:
            raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")

        # Update segments in transcription
        transcription.segments = segments

        # Regenerate full transcription text
        transcription.transcription_text = "\n".join([
            seg.get("text", "").strip() for seg in segments if seg.get("text")
        ])

        # Recalculate word count
        transcription.word_count = len(transcription.transcription_text.split())

        # Mark the segments column as modified (required for JSONB)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(transcription, "segments")

        await self.db.commit()
        await self.db.refresh(transcription)

        return transcription
