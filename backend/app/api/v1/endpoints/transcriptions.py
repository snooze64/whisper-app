"""
Transcription API endpoints
"""
import os
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.transcription import (
    TranscriptionResponse,
    TranscriptionUpdate,
    SegmentUpdateRequest,
)
from app.services.transcription_service import TranscriptionService
from app.utils.subtitle import save_subtitle_file

router = APIRouter()


@router.get("/tasks/{task_id}/transcription", response_model=TranscriptionResponse)
async def get_transcription(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get transcription result by task ID

    - **task_id**: Task UUID

    Returns transcription with full text, segments, and metadata.
    Users can only access transcriptions from their own tasks unless they are admins.
    """
    transcription_service = TranscriptionService(db)
    transcription = await transcription_service.get_transcription_by_task_id(
        task_id=task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )

    return transcription


@router.put("/tasks/{task_id}/transcription", response_model=TranscriptionResponse)
async def update_transcription(
    task_id: UUID,
    transcription_data: TranscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update transcription result

    - **task_id**: Task UUID
    - **transcription_data**: Fields to update (transcription_text, segments, word_count)

    Users can only update transcriptions from their own tasks unless they are admins.
    """
    transcription_service = TranscriptionService(db)
    transcription = await transcription_service.update_transcription(
        task_id=task_id,
        transcription_data=transcription_data,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )

    return transcription


@router.patch("/tasks/{task_id}/transcription/segments", response_model=TranscriptionResponse)
async def update_segment(
    task_id: UUID,
    segment_data: SegmentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a single segment in the transcription

    - **task_id**: Task UUID
    - **segment_data**: Segment ID and fields to update (text, start, end, speaker_label)

    Users can only update segments from their own tasks unless they are admins.
    This endpoint is useful for fine-grained editing of individual segments.
    """
    transcription_service = TranscriptionService(db)
    transcription = await transcription_service.update_segment(
        task_id=task_id,
        segment_id=segment_data.segment_id,
        text=segment_data.text,
        start=segment_data.start,
        end=segment_data.end,
        speaker_label=segment_data.speaker_label,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )

    return transcription


@router.get("/tasks/{task_id}/text")
async def download_text(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download transcription as plain text file

    - **task_id**: Task UUID

    Returns plain text file with transcription result.
    Users can only download text from their own tasks unless they are admins.
    """
    transcription_service = TranscriptionService(db)
    transcription = await transcription_service.get_transcription_by_task_id(
        task_id=task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )

    # Generate plain text file dynamically
    try:
        # Create temp directory
        temp_dir = Path("/data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Generate text file
        text_path = temp_dir / f"{task_id}_transcription.txt"

        # Write transcription text to file
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(transcription.transcription_text)

        # Return file
        filename = f"transcription_{task_id}.txt"
        return FileResponse(
            path=str(text_path),
            media_type="text/plain; charset=utf-8",
            filename=filename
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate text file: {str(e)}")


@router.get("/tasks/{task_id}/subtitle")
async def download_subtitle(
    task_id: UUID,
    format: str = Query("srt", regex="^(srt|vtt)$", description="Subtitle format (srt or vtt)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download subtitle file

    - **task_id**: Task UUID
    - **format**: Subtitle format ("srt" or "vtt")

    Returns subtitle file for download.
    Users can only download subtitles from their own tasks unless they are admins.
    """
    transcription_service = TranscriptionService(db)
    transcription = await transcription_service.get_transcription_by_task_id(
        task_id=task_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin
    )

    # Generate subtitle file dynamically
    try:
        # Create temp directory for subtitle generation
        temp_dir = Path("/data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Generate subtitle file
        base_path = temp_dir / f"{task_id}_download"
        subtitle_path = save_subtitle_file(
            segments=transcription.segments,
            file_path=str(base_path),
            format=format
        )

        # Check if file exists
        if not os.path.exists(subtitle_path):
            raise HTTPException(status_code=404, detail="Subtitle file not found")

        # Return file
        filename = f"transcription_{task_id}.{format}"
        return FileResponse(
            path=subtitle_path,
            media_type="text/plain",
            filename=filename
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate subtitle: {str(e)}")
