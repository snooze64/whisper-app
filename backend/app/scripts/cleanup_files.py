"""
Automatic file cleanup script

This script removes uploaded files and processing results that are older than
the configured retention period.

Run as a scheduled task (cron job) in production.
"""
import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.task import Task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def cleanup_old_files():
    """
    Remove files older than FILE_RETENTION_HOURS
    """
    retention_hours = int(os.getenv('FILE_RETENTION_HOURS', '24'))
    cutoff_time = datetime.utcnow() - timedelta(hours=retention_hours)

    logger.info(f"Starting file cleanup (retention: {retention_hours} hours)")
    logger.info(f"Removing files older than: {cutoff_time}")

    # Create database session
    # Convert DATABASE_URL to use asyncpg driver for async operations
    database_url = settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    deleted_count = 0
    error_count = 0

    async with async_session() as session:
        # Find old completed or failed tasks
        result = await session.execute(
            select(Task).where(
                and_(
                    Task.created_at < cutoff_time,
                    Task.status.in_(['completed', 'failed'])
                )
            )
        )
        old_tasks = result.scalars().all()

        logger.info(f"Found {len(old_tasks)} tasks to clean up")

        for task in old_tasks:
            try:
                # Delete uploaded file
                if task.file_path and os.path.exists(task.file_path):
                    os.remove(task.file_path)
                    logger.debug(f"Deleted file: {task.file_path}")
                    deleted_count += 1

                # Delete result files (transcription text, subtitles)
                # Result files are typically in /data/results/{task_id}/
                result_dir = Path(f"/data/results/{task.id}")
                if result_dir.exists():
                    for file in result_dir.glob("*"):
                        file.unlink()
                        deleted_count += 1
                    result_dir.rmdir()
                    logger.debug(f"Deleted result directory: {result_dir}")

                # Delete temp files
                temp_dir = Path(f"/data/temp/{task.id}")
                if temp_dir.exists():
                    for file in temp_dir.glob("*"):
                        file.unlink()
                        deleted_count += 1
                    temp_dir.rmdir()
                    logger.debug(f"Deleted temp directory: {temp_dir}")

            except Exception as e:
                logger.error(f"Error deleting files for task {task.id}: {e}")
                error_count += 1

    await engine.dispose()

    logger.info("=" * 50)
    logger.info("Cleanup Summary:")
    logger.info(f"  Tasks processed: {len(old_tasks)}")
    logger.info(f"  Files deleted: {deleted_count}")
    logger.info(f"  Errors: {error_count}")
    logger.info("=" * 50)

    return deleted_count, error_count


async def cleanup_orphaned_files():
    """
    Remove files that don't have a corresponding database entry
    """
    logger.info("Checking for orphaned files...")

    # Create database session
    # Convert DATABASE_URL to use asyncpg driver for async operations
    database_url = settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    deleted_count = 0

    async with async_session() as session:
        # Get all task IDs
        result = await session.execute(select(Task.id))
        valid_task_ids = set(str(task_id) for task_id, in result.fetchall())

        # Check upload directory
        upload_dir = Path("/data/uploads")
        if upload_dir.exists():
            for user_dir in upload_dir.iterdir():
                if not user_dir.is_dir():
                    continue

                for file in user_dir.iterdir():
                    # Extract task ID from filename (assuming format: {task_id}_{filename})
                    task_id = file.stem.split('_')[0]
                    if task_id not in valid_task_ids:
                        try:
                            file.unlink()
                            logger.info(f"Deleted orphaned file: {file}")
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"Error deleting orphaned file {file}: {e}")

        # Check result directory
        result_dir = Path("/data/results")
        if result_dir.exists():
            for task_dir in result_dir.iterdir():
                if not task_dir.is_dir():
                    continue

                task_id = task_dir.name
                if task_id not in valid_task_ids:
                    try:
                        for file in task_dir.glob("*"):
                            file.unlink()
                        task_dir.rmdir()
                        logger.info(f"Deleted orphaned result directory: {task_dir}")
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting orphaned directory {task_dir}: {e}")

    await engine.dispose()

    logger.info(f"Orphaned files cleanup complete. Deleted: {deleted_count}")
    return deleted_count


async def main():
    """
    Main cleanup function
    """
    try:
        logger.info("Starting file cleanup service...")

        # Cleanup old files
        deleted, errors = await cleanup_old_files()

        # Cleanup orphaned files (once per day)
        hour = datetime.utcnow().hour
        if hour == 3:  # Run at 3 AM UTC
            orphaned = await cleanup_orphaned_files()
            logger.info(f"Orphaned files deleted: {orphaned}")

        logger.info("File cleanup completed successfully")

    except Exception as e:
        logger.error(f"File cleanup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run cleanup in a loop (hourly checks)
    while True:
        asyncio.run(main())
        # Sleep for 1 hour
        asyncio.run(asyncio.sleep(3600))
