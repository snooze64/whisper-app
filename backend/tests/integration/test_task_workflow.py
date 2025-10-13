"""
Integration tests for task workflow (file upload → transcription → completion)
"""
import pytest
import asyncio
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.models.user import User
from app.models.task import Task
from app.models.transcription import Transcription
from app.models.processing_history import ProcessingHistory


@pytest.mark.asyncio
async def test_complete_task_workflow(test_db: AsyncSession, test_user: User, user_token: str):
    """
    Test complete workflow: upload file → create task → process → retrieve results

    This is an integration test that verifies the entire flow works together.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Upload a file and create a task
        test_file_content = b"fake audio data"
        files = {"file": ("test.mp3", test_file_content, "audio/mpeg")}
        data = {
            "model_name": "tiny",
            "language": "ja",
            "num_speakers": 2
        }

        response = await client.post(
            "/api/v1/upload",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == 200
        upload_data = response.json()
        task_id = upload_data["task_id"]

        # Verify task was created in database
        result = await test_db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one()
        assert task.status == "pending"
        assert task.user_id == test_user.id
        assert task.model_name == "tiny"
        assert task.language == "ja"
        assert task.num_speakers == 2

        # Step 2: Simulate task processing (normally done by Celery)
        # Update task to processing status
        task.status = "processing"
        task.progress = 50
        await test_db.commit()

        # Check task status endpoint
        response = await client.get(
            f"/api/v1/tasks/{task_id}/status",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["status"] == "processing"
        assert status_data["progress"] == 50

        # Step 3: Simulate task completion
        task.status = "completed"
        task.progress = 100
        await test_db.commit()

        # Create transcription result
        transcription = Transcription(
            task_id=task_id,
            transcription_text="This is a test transcription.",
            segments=[
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 2.5,
                    "text": "This is",
                    "speaker_id": 1,
                    "speaker_label": "Speaker 1",
                    "confidence": 0.95
                },
                {
                    "id": 1,
                    "start": 2.5,
                    "end": 5.0,
                    "text": "a test transcription.",
                    "speaker_id": 2,
                    "speaker_label": "Speaker 2",
                    "confidence": 0.92
                }
            ],
            word_count=5
        )
        test_db.add(transcription)

        # Create processing history
        history = ProcessingHistory(
            task_id=task_id,
            user_id=test_user.id,
            processing_time_seconds=120.5,
            gpu_memory_used_mb=4096,
            model_name="tiny",
            file_format="mp3",
            file_size_mb=10.0,
            success=True,
            error_type=None
        )
        test_db.add(history)
        await test_db.commit()

        # Step 4: Retrieve transcription results
        response = await client.get(
            f"/api/v1/tasks/{task_id}/transcription",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        transcription_data = response.json()
        assert transcription_data["transcription_text"] == "This is a test transcription."
        assert len(transcription_data["segments"]) == 2
        assert transcription_data["word_count"] == 5

        # Verify segments have speaker information
        assert transcription_data["segments"][0]["speaker_id"] == 1
        assert transcription_data["segments"][0]["speaker_label"] == "Speaker 1"
        assert transcription_data["segments"][1]["speaker_id"] == 2
        assert transcription_data["segments"][1]["speaker_label"] == "Speaker 2"

        # Step 5: Retrieve processing history
        response = await client.get(
            "/api/v1/history",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        history_data = response.json()
        assert history_data["total"] >= 1

        # Find our history entry
        our_history = next(
            (h for h in history_data["items"] if h["task_id"] == task_id),
            None
        )
        assert our_history is not None
        assert our_history["success"] is True
        assert our_history["processing_time_seconds"] == 120.5
        assert our_history["model_name"] == "tiny"

        # Step 6: Delete task
        response = await client.delete(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 204

        # Verify task is deleted
        result = await test_db.execute(
            select(Task).where(Task.id == task_id)
        )
        deleted_task = result.scalar_one_or_none()
        assert deleted_task is None

        # Verify transcription is also deleted (CASCADE)
        result = await test_db.execute(
            select(Transcription).where(Transcription.task_id == task_id)
        )
        deleted_transcription = result.scalar_one_or_none()
        assert deleted_transcription is None

        # Processing history should remain (for statistics)
        result = await test_db.execute(
            select(ProcessingHistory).where(ProcessingHistory.task_id == task_id)
        )
        remaining_history = result.scalar_one_or_none()
        assert remaining_history is not None


@pytest.mark.asyncio
async def test_task_failure_workflow(test_db: AsyncSession, test_user: User, user_token: str):
    """
    Test workflow when task processing fails
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a task
        test_file_content = b"fake audio data"
        files = {"file": ("test_fail.mp3", test_file_content, "audio/mpeg")}
        data = {
            "model_name": "tiny",
            "language": "ja"
        }

        response = await client.post(
            "/api/v1/upload",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == 200
        task_id = response.json()["task_id"]

        # Simulate task failure
        result = await test_db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one()
        task.status = "failed"
        task.error_message = "GPU out of memory"
        await test_db.commit()

        # Create failure history
        history = ProcessingHistory(
            task_id=task_id,
            user_id=test_user.id,
            processing_time_seconds=30.0,
            gpu_memory_used_mb=0,
            model_name="tiny",
            file_format="mp3",
            file_size_mb=10.0,
            success=False,
            error_type="GPU_OOM"
        )
        test_db.add(history)
        await test_db.commit()

        # Check task status shows failure
        response = await client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        task_data = response.json()
        assert task_data["status"] == "failed"
        assert task_data["error_message"] == "GPU out of memory"

        # Verify failure is recorded in history
        response = await client.get(
            "/api/v1/history",
            params={"success": "false"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        history_data = response.json()

        our_history = next(
            (h for h in history_data["items"] if h["task_id"] == task_id),
            None
        )
        assert our_history is not None
        assert our_history["success"] is False
        assert our_history["error_type"] == "GPU_OOM"


@pytest.mark.asyncio
async def test_concurrent_tasks_same_user(test_db: AsyncSession, test_user: User, user_token: str):
    """
    Test that a user can have multiple concurrent tasks
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create multiple tasks concurrently
        task_ids = []
        for i in range(3):
            test_file_content = f"fake audio data {i}".encode()
            files = {"file": (f"test{i}.mp3", test_file_content, "audio/mpeg")}
            data = {
                "model_name": "tiny",
                "language": "ja"
            }

            response = await client.post(
                "/api/v1/upload",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {user_token}"}
            )

            assert response.status_code == 200
            task_ids.append(response.json()["task_id"])

        # Verify all tasks exist
        result = await test_db.execute(
            select(Task).where(Task.user_id == test_user.id)
        )
        tasks = result.scalars().all()
        assert len(tasks) >= 3

        # Get task list via API
        response = await client.get(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        tasks_data = response.json()
        assert tasks_data["total"] >= 3

        # Verify all our task IDs are in the list
        api_task_ids = [t["id"] for t in tasks_data["tasks"]]
        for task_id in task_ids:
            assert task_id in api_task_ids


@pytest.mark.asyncio
async def test_transcription_edit_workflow(test_db: AsyncSession, completed_task: Task, user_token: str):
    """
    Test editing transcription segments
    """
    # Create transcription
    transcription = Transcription(
        task_id=completed_task.id,
        transcription_text="Original text",
        segments=[
            {
                "id": 0,
                "start": 0.0,
                "end": 2.0,
                "text": "Original segment",
                "speaker_id": 1,
                "speaker_label": "Speaker 1"
            }
        ],
        word_count=2
    )
    test_db.add(transcription)
    await test_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Edit segment
        update_data = {
            "segment_id": 0,
            "text": "Updated segment text",
            "start": 0.0,
            "end": 2.5
        }

        response = await client.patch(
            f"/api/v1/tasks/{completed_task.id}/transcription/segments",
            json=update_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == 200
        result_data = response.json()

        # Verify segment was updated
        assert result_data["segments"][0]["text"] == "Updated segment text"
        assert result_data["segments"][0]["end"] == 2.5

        # Verify full text was recalculated
        assert "Updated segment text" in result_data["transcription_text"]

        # Verify changes persisted to database
        await test_db.refresh(transcription)
        assert transcription.segments[0]["text"] == "Updated segment text"
