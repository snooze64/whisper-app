"""
Whisper transcription Celery tasks

Main transcription processing tasks using faster-whisper.
"""
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from celery import Task, chain, group
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.db.session import get_db_context
from app.models.task import Task as TaskModel
from app.tasks.audio_extraction import extract_audio, get_audio_duration, cleanup_temp_audio
from app.tasks.gpu_monitor import get_gpu_monitor, get_model_memory_requirement

logger = logging.getLogger(__name__)

# Try to import faster-whisper
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
    logger.info("faster-whisper available")
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not available - using mock mode")


class WhisperTranscriber:
    """
    Whisper transcription wrapper using faster-whisper
    """

    def __init__(self, model_name: str = "large-v3-turbo", device: str = "cuda", compute_type: str = "float16"):
        """
        Initialize Whisper transcriber

        Args:
            model_name: Model name (e.g., "large-v3", "large-v3-turbo")
            device: Device to use ("cuda" or "cpu")
            compute_type: Computation type ("float16", "int8_float16", "int8")
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.model = None

        logger.info(f"Initializing Whisper transcriber: model={model_name}, device={device}, compute_type={compute_type}")

    def load_model(self):
        """Load Whisper model"""
        if not FASTER_WHISPER_AVAILABLE:
            logger.warning("faster-whisper not available - skipping model load")
            return

        try:
            # Check GPU memory before loading
            gpu_monitor = get_gpu_monitor()
            required_mb = get_model_memory_requirement(self.model_name)

            if self.device == "cuda" and not gpu_monitor.check_available_memory(required_mb):
                logger.error(f"Insufficient GPU memory for model {self.model_name} (requires {required_mb}MB)")
                raise RuntimeError(f"Insufficient GPU memory: requires {required_mb}MB")

            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("Whisper model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe(
        self,
        audio_file: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        beam_size: int = 5,
        vad_filter: bool = True,
        vad_parameters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribe audio file

        Args:
            audio_file: Path to audio file
            language: Language code (e.g., "ja", "en") or None for auto-detection
            task: Task type ("transcribe" or "translate")
            beam_size: Beam size for decoding
            vad_filter: Enable VAD (Voice Activity Detection) filter
            vad_parameters: VAD parameters

        Returns:
            List of segments with transcription results
        """
        if not FASTER_WHISPER_AVAILABLE or self.model is None:
            # Return mock data for development
            logger.warning("Using mock transcription")
            return self._mock_transcribe(audio_file)

        try:
            logger.info(f"Transcribing audio file: {audio_file}")
            logger.info(f"Parameters: language={language}, task={task}, beam_size={beam_size}, vad_filter={vad_filter}")

            # Transcribe
            segments, info = self.model.transcribe(
                audio_file,
                language=language,
                task=task,
                beam_size=beam_size,
                vad_filter=vad_filter,
                vad_parameters=vad_parameters or {}
            )

            logger.info(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
            logger.info(f"Duration: {info.duration:.2f} seconds")

            # Convert segments to list
            result_segments = []
            for i, segment in enumerate(segments):
                result_segments.append({
                    "id": i,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "avg_logprob": segment.avg_logprob,
                    "no_speech_prob": segment.no_speech_prob,
                    "words": [
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability
                        }
                        for word in (segment.words or [])
                    ] if hasattr(segment, 'words') and segment.words else []
                })

            logger.info(f"Transcription complete: {len(result_segments)} segments")
            return result_segments

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def _mock_transcribe(self, audio_file: str) -> List[Dict[str, Any]]:
        """
        Mock transcription for development environment

        Args:
            audio_file: Path to audio file

        Returns:
            Mock transcription segments
        """
        duration = get_audio_duration(audio_file) or 60.0

        # Generate mock segments (every 5 seconds)
        segments = []
        num_segments = int(duration / 5) + 1

        for i in range(num_segments):
            start = i * 5.0
            end = min((i + 1) * 5.0, duration)

            segments.append({
                "id": i,
                "start": start,
                "end": end,
                "text": f"S�o�ï�WwSWP�gY����� {i + 1}",
                "avg_logprob": -0.3,
                "no_speech_prob": 0.1,
                "words": []
            })

        logger.info(f"Mock transcription: {len(segments)} segments for {duration:.2f} seconds")
        return segments


# Celery tasks

@celery_app.task(bind=True, max_retries=3)
def extract_audio_task(self: Task, task_id: str, input_file: str) -> Dict[str, Any]:
    """
    Extract audio from uploaded file

    Args:
        task_id: Task UUID
        input_file: Path to uploaded file

    Returns:
        Dictionary with extracted audio file path and duration
    """
    logger.info(f"Starting audio extraction for task {task_id}")

    try:
        # Update task status
        with get_db_context() as db:
            result = db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()
            if task:
                task.status = "processing"
                task.progress = 10
                db.commit()

        # Extract audio to temp directory
        temp_dir = Path("/data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_file = temp_dir / f"{task_id}.wav"

        # Extract audio
        extracted_audio = extract_audio(
            input_file=input_file,
            output_file=str(output_file),
            sample_rate=16000,
            channels=1
        )

        # Get audio duration
        duration = get_audio_duration(extracted_audio)

        logger.info(f"Audio extraction complete: {extracted_audio} ({duration:.2f}s)")

        # Update progress
        with get_db_context() as db:
            result = db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()
            if task:
                task.progress = 20
                db.commit()

        return {
            "audio_file": extracted_audio,
            "duration": duration
        }

    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")

        # Update task status to failed
        try:
            with get_db_context() as db:
                result = db.execute(
                    select(TaskModel).where(TaskModel.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.error_message = f"Audio extraction failed: {str(e)}"
                    db.commit()
        except:
            pass

        raise self.retry(exc=e, countdown=60)  # Retry after 1 minute


@celery_app.task(bind=True, max_retries=2)
def transcribe_audio_task(
    self: Task,
    audio_result: Dict[str, Any],
    task_id: str,
    model_name: str,
    language: str
) -> Dict[str, Any]:
    """
    Transcribe audio file using Whisper

    Args:
        audio_result: Result from extract_audio_task (contains audio_file and duration)
        task_id: Task UUID
        model_name: Whisper model name
        language: Language code

    Returns:
        Dictionary with segments and audio_file
    """
    audio_file = audio_result.get("audio_file")
    if not audio_file:
        raise ValueError("audio_file not found in audio_result")
    logger.info(f"Starting transcription for task {task_id}")
    logger.info(f"Model: {model_name}, Language: {language}")

    try:
        # Update progress
        with get_db_context() as db:
            result = db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()
            if task:
                task.progress = 30
                db.commit()

        # Initialize transcriber
        device = "cuda" if FASTER_WHISPER_AVAILABLE else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"

        transcriber = WhisperTranscriber(
            model_name=model_name,
            device=device,
            compute_type=compute_type
        )

        # Load model
        transcriber.load_model()

        # Update progress
        with get_db_context() as db:
            result = db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()
            if task:
                task.progress = 50
                db.commit()

        # Transcribe
        segments = transcriber.transcribe(
            audio_file=audio_file,
            language=language if language != "auto" else None,
            vad_filter=True
        )

        logger.info(f"Transcription complete: {len(segments)} segments")

        # Update progress
        with get_db_context() as db:
            result = db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()
            if task:
                task.progress = 80
                db.commit()

        return {
            "segments": segments,
            "audio_file": audio_file
        }

    except Exception as e:
        logger.error(f"Transcription failed: {e}")

        # Update task status to failed
        try:
            with get_db_context() as db:
                result = db.execute(
                    select(TaskModel).where(TaskModel.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.error_message = f"Transcription failed: {str(e)}"
                    db.commit()
        except:
            pass

        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes


@celery_app.task(bind=True)
def save_transcription_result(
    self: Task,
    transcription_result: Dict[str, Any],
    task_id: str
) -> Dict[str, Any]:
    """
    Save transcription result to database

    Args:
        transcription_result: Result from transcribe_audio_task (contains segments and audio_file)
        task_id: Task UUID

    Returns:
        Result summary
    """
    segments = transcription_result.get("segments")
    audio_file = transcription_result.get("audio_file")

    if not segments:
        raise ValueError("segments not found in transcription_result")
    if not audio_file:
        raise ValueError("audio_file not found in transcription_result")

    logger.info(f"Saving transcription result for task {task_id}")

    try:
        # Save to database
        with get_db_context() as db:
            result = db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()

            if not task:
                raise ValueError(f"Task not found: {task_id}")

            # Update task
            task.status = "completed"
            task.progress = 100
            task.completed_at = datetime.utcnow()

            # TODO: Save segments to transcriptions table (Phase 6)
            # For now, just store segment count in progress field as verification
            logger.info(f"Segments to save: {len(segments)}")

            db.commit()

        # Cleanup temporary audio file
        cleanup_temp_audio(audio_file)

        logger.info(f"Transcription result saved successfully for task {task_id}")

        return {
            "task_id": task_id,
            "segment_count": len(segments),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Failed to save transcription result: {e}")

        # Update task status to failed
        try:
            with get_db_context() as db:
                result = db.execute(
                    select(TaskModel).where(TaskModel.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.error_message = f"Failed to save result: {str(e)}"
                    db.commit()
        except:
            pass

        raise


def start_transcription_workflow(task_id: str, file_path: str, model_name: str, language: str):
    """
    Start transcription workflow (task chain)

    Args:
        task_id: Task UUID
        file_path: Path to uploaded file
        model_name: Whisper model name
        language: Language code
    """
    logger.info(f"Starting transcription workflow for task {task_id}")

    # Create task chain: extract_audio -> transcribe -> save_result
    # Note: chain passes result from previous task as first argument to next task
    workflow = (
        extract_audio_task.si(task_id, file_path) |  # signature with immutable args
        transcribe_audio_task.s(task_id, model_name, language) |  # receives audio_file from extract_audio_task
        save_transcription_result.s(task_id)  # receives segments from transcribe_audio_task
    )

    # Execute workflow asynchronously
    workflow.apply_async()

    logger.info(f"Transcription workflow started for task {task_id}")
