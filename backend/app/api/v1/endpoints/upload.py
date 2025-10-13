"""
Upload API endpoints
"""
import logging
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse
from app.services.file_service import FileService
from app.services.task_service import TaskService
from app.tasks.transcription_tasks import start_transcription_workflow

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=TaskResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(..., description="Audio or video file"),
    model: str = Form(..., description="Whisper model (large-v3, large-v3-turbo)"),
    language: str = Form(default="ja", description="Language code"),
    num_speakers: int = Form(default=None, description="Number of speakers (optional)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload file for transcription

    - **file**: Audio (mp3, wav) or video (mp4) file
    - **model**: Whisper model to use
    - **language**: Language code (default: ja)
    - **num_speakers**: Number of speakers for diarization (optional)

    Returns task information with UUID
    """
    # Save uploaded file
    file_path, filename, file_size = await FileService.save_upload_file(
        file=file,
        user_id=current_user.id
    )

    # Get file format
    file_format = FileService.validate_file_format(filename)

    # Create task data
    task_data = TaskCreate(
        filename=filename,
        file_size=file_size,
        file_format=file_format,
        model_name=model,
        language=language,
        num_speakers=num_speakers
    )

    # Create task in database
    task_service = TaskService(db)
    task = await task_service.create_task(
        task_data=task_data,
        file_path=file_path,
        user_id=current_user.id
    )

    # Start transcription workflow (Celery task chain)
    try:
        start_transcription_workflow(
            task_id=str(task.id),
            file_path=file_path,
            model_name=model,
            language=language,
            num_speakers=num_speakers
        )
        logger.info(f"Started transcription workflow for task {task.id}")
    except Exception as e:
        logger.error(f"Failed to start transcription workflow: {e}")
        # Task is already created, workflow will be retried or can be manually restarted

    return task
