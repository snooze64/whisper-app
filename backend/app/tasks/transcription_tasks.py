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
from app.models.transcription import Transcription
from app.models.processing_history import ProcessingHistory
from app.tasks.audio_extraction import extract_audio, get_audio_duration, cleanup_temp_audio
from app.tasks.gpu_monitor import get_gpu_monitor, get_model_memory_requirement
from app.tasks.diarization import get_diarizer
from app.utils.subtitle import save_subtitle_file
from decimal import Decimal

logger = logging.getLogger(__name__)

# Backend selection via environment variable
# WHISPER_BACKEND: "faster-whisper" (default) or "transformers"
WHISPER_BACKEND = os.getenv("WHISPER_BACKEND", "faster-whisper")

# Try to import faster-whisper
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
    logger.info("faster-whisper available")
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not available - using mock mode")

# Try to import transformers-based implementation
try:
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers
    TRANSFORMERS_AVAILABLE = True
    logger.info("transformers backend available")
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers backend not available")


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


def get_transcriber(model_name: str, device: str, compute_type: str):
    """
    Factory function to create appropriate Whisper transcriber based on backend selection

    Args:
        model_name: Whisper model name
        device: Device to use ("cuda" or "cpu")
        compute_type: Computation type for faster-whisper or torch dtype for transformers

    Returns:
        Transcriber instance (WhisperTranscriber or WhisperTranscriberTransformers)
    """
    backend = WHISPER_BACKEND.lower()

    logger.info(f"Creating transcriber: backend={backend}, model={model_name}, device={device}, compute_type={compute_type}")

    if backend == "transformers":
        if not TRANSFORMERS_AVAILABLE:
            logger.error("transformers backend requested but not available, falling back to faster-whisper")
            backend = "faster-whisper"
        else:
            # Use transformers backend
            logger.info("Using transformers backend (HuggingFace Whisper)")

            # Map compute_type to torch_dtype
            # faster-whisper compute_type: "float16", "int8_float16", "int8"
            # transformers torch_dtype: "float16", "float32", "int8"
            torch_dtype_map = {
                "float16": "float16",
                "int8_float16": "float16",  # Use float16 as closest match
                "int8": "int8",
                "float32": "float32"
            }
            torch_dtype = torch_dtype_map.get(compute_type, "float16")

            return WhisperTranscriberTransformers(
                model_name=model_name,
                device=device,
                torch_dtype=torch_dtype
            )

    # Use faster-whisper backend (default)
    if not FASTER_WHISPER_AVAILABLE:
        logger.warning("faster-whisper not available, transcriber will use mock mode")

    logger.info("Using faster-whisper backend (CTranslate2)")
    return WhisperTranscriber(
        model_name=model_name,
        device=device,
        compute_type=compute_type
    )


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
        # Check if GPU is actually available via gpu_monitor
        gpu_monitor = get_gpu_monitor()

        # Determine if we can use CUDA based on backend availability
        backend_available = (
            (WHISPER_BACKEND == "transformers" and TRANSFORMERS_AVAILABLE) or
            (WHISPER_BACKEND == "faster-whisper" and FASTER_WHISPER_AVAILABLE)
        )
        device = "cuda" if (backend_available and gpu_monitor.initialized) else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"

        logger.info(f"Device selection: backend={WHISPER_BACKEND}, device={device}, compute_type={compute_type}, gpu_available={gpu_monitor.initialized}")

        # Use factory function to get appropriate transcriber backend
        transcriber = get_transcriber(
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


@celery_app.task(bind=True, max_retries=2)
def diarize_audio_task(
    self: Task,
    transcription_result: Dict[str, Any],
    task_id: str,
    num_speakers: Optional[int] = None
) -> Dict[str, Any]:
    """
    Perform speaker diarization on transcribed segments

    Args:
        transcription_result: Result from transcribe_audio_task (contains segments and audio_file)
        task_id: Task UUID
        num_speakers: Number of speakers (if None, auto-detect)

    Returns:
        Dictionary with diarized segments and audio_file
    """
    segments = transcription_result.get("segments")
    audio_file = transcription_result.get("audio_file")

    if not segments:
        raise ValueError("segments not found in transcription_result")
    if not audio_file:
        raise ValueError("audio_file not found in transcription_result")

    logger.info(f"Starting diarization for task {task_id}")
    logger.info(f"Number of speakers: {num_speakers or 'auto-detect'}")

    try:
        # Update progress
        with get_db_context() as db:
            result = db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()
            if task:
                task.progress = 85
                db.commit()

        # Initialize diarizer
        diarizer = get_diarizer()

        # Perform diarization
        diarized_segments = diarizer.diarize(
            audio_file=audio_file,
            segments=segments,
            num_speakers=num_speakers
        )

        logger.info(f"Diarization complete: {len(diarized_segments)} segments with speaker labels")

        # Update progress
        with get_db_context() as db:
            result = db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()
            if task:
                task.progress = 90
                db.commit()

        return {
            "segments": diarized_segments,
            "audio_file": audio_file
        }

    except Exception as e:
        logger.error(f"Diarization failed: {e}")

        # Update task status to failed
        try:
            with get_db_context() as db:
                result = db.execute(
                    select(TaskModel).where(TaskModel.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.error_message = f"Diarization failed: {str(e)}"
                    db.commit()
        except:
            pass

        raise self.retry(exc=e, countdown=120)  # Retry after 2 minutes


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

            # Create full transcription text by concatenating all segments
            transcription_text = "\n".join([seg.get("text", "").strip() for seg in segments if seg.get("text")])

            # Calculate word count (rough estimate by splitting on whitespace)
            word_count = len(transcription_text.split())

            # Generate subtitle files (SRT format by default)
            subtitle_path = None
            try:
                # Create subtitles directory if it doesn't exist
                subtitle_dir = Path("/data/subtitles")
                subtitle_dir.mkdir(parents=True, exist_ok=True)

                # Generate SRT subtitle file
                base_path = subtitle_dir / str(task_id)
                subtitle_path = save_subtitle_file(segments, str(base_path), format="srt")
                logger.info(f"Generated subtitle file: {subtitle_path}")
            except Exception as e:
                logger.error(f"Failed to generate subtitle file: {e}")
                # Continue even if subtitle generation fails
                subtitle_path = None

            # Create Transcription record
            transcription = Transcription(
                task_id=task.id,
                transcription_text=transcription_text,
                segments=segments,
                subtitle_path=subtitle_path,
                word_count=word_count
            )
            db.add(transcription)

            # Update task
            task.status = "completed"
            task.progress = 100
            task.completed_at = datetime.utcnow()

            logger.info(f"Saved transcription: {len(segments)} segments, {word_count} words")

            # Create processing history record
            try:
                # Calculate processing time in seconds
                processing_time = int((task.completed_at - task.created_at).total_seconds())

                # Try to get GPU memory usage
                gpu_memory_used_mb = None
                try:
                    gpu_monitor = get_gpu_monitor()
                    if gpu_monitor.initialized:
                        gpu_info = gpu_monitor.get_gpu_info()
                        if gpu_info and 'memory_used' in gpu_info:
                            gpu_memory_used_mb = gpu_info['memory_used']
                except Exception:
                    pass  # GPU info not available

                # Convert file size to MB
                file_size_mb = Decimal(str(task.file_size / (1024 * 1024)))

                # Create history record
                history = ProcessingHistory(
                    task_id=task.id,
                    user_id=task.user_id,
                    processing_time_seconds=processing_time,
                    gpu_memory_used_mb=gpu_memory_used_mb,
                    model_name=task.model_name,
                    file_format=task.file_format,
                    file_size_mb=file_size_mb,
                    success=True,
                    error_type=None
                )
                db.add(history)
                logger.info(f"Created processing history record for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to create processing history record: {e}")
                # Don't fail the task if history recording fails

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

        # Update task status to failed and create failure history record
        try:
            with get_db_context() as db:
                result = db.execute(
                    select(TaskModel).where(TaskModel.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.error_message = f"Failed to save result: {str(e)}"
                    task.completed_at = datetime.utcnow()

                    # Create failure history record
                    try:
                        processing_time = int((task.completed_at - task.created_at).total_seconds())
                        file_size_mb = Decimal(str(task.file_size / (1024 * 1024)))

                        history = ProcessingHistory(
                            task_id=task.id,
                            user_id=task.user_id,
                            processing_time_seconds=processing_time,
                            gpu_memory_used_mb=None,
                            model_name=task.model_name,
                            file_format=task.file_format,
                            file_size_mb=file_size_mb,
                            success=False,
                            error_type="save_result_error"
                        )
                        db.add(history)
                        logger.info(f"Created failure history record for task {task_id}")
                    except Exception as hist_error:
                        logger.error(f"Failed to create failure history record: {hist_error}")

                    db.commit()
        except:
            pass

        raise


def start_transcription_workflow(
    task_id: str,
    file_path: str,
    model_name: str,
    language: str,
    num_speakers: Optional[int] = None
):
    """
    Start transcription workflow (task chain)

    Args:
        task_id: Task UUID
        file_path: Path to uploaded file
        model_name: Whisper model name
        language: Language code
        num_speakers: Number of speakers for diarization (if None, auto-detect)
    """
    logger.info(f"Starting transcription workflow for task {task_id}")

    # Create task chain: extract_audio -> transcribe -> diarize -> save_result
    # Note: chain passes result from previous task as first argument to next task
    workflow = (
        extract_audio_task.si(task_id, file_path) |  # signature with immutable args
        transcribe_audio_task.s(task_id, model_name, language) |  # receives audio_file from extract_audio_task
        diarize_audio_task.s(task_id, num_speakers) |  # receives segments from transcribe_audio_task
        save_transcription_result.s(task_id)  # receives diarized segments from diarize_audio_task
    )

    # Execute workflow asynchronously
    workflow.apply_async()

    logger.info(f"Transcription workflow started for task {task_id}")
