"""
Celery application configuration
"""
from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "whisper_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.transcription_tasks",
        # Phase 4 complete: audio_extraction is imported within transcription_tasks
        # Phase 5 complete: diarization is imported within transcription_tasks
        # "app.tasks.subtitle",  # Phase 6 - TODO
        # "app.tasks.cleanup",  # Phase 7 - TODO
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    # Route transcription tasks to 'transcription' queue
    task_routes={
        "app.tasks.transcription_tasks.*": {"queue": "transcription"},
    },

    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Acknowledge task after completion

    # Task time limits
    task_time_limit=10800,  # 3 hours hard limit
    task_soft_time_limit=10200,  # 2h50m soft limit

    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,

    # Task priority
    task_queue_max_priority=10,
    task_default_priority=5,
)

# Task priority constants
HIGH_PRIORITY = 9
NORMAL_PRIORITY = 5
LOW_PRIORITY = 1


if __name__ == "__main__":
    celery_app.start()
