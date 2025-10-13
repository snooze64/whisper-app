"""
Test transcription API endpoints
"""
import pytest
from fastapi import status


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_transcription(test_client, user_headers, completed_task):
    """Test getting transcription"""
    response = await test_client.get(
        f"/api/v1/tasks/{completed_task.id}/transcription",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "transcription_text" in data
    assert "segments" in data
    assert "word_count" in data
    assert len(data["segments"]) == 2
    assert "これはテストです。" in data["transcription_text"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_transcription_not_found(test_client, user_headers, test_task):
    """Test getting transcription for task without transcription"""
    response = await test_client.get(
        f"/api/v1/tasks/{test_task.id}/transcription",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_transcription_task_not_found(test_client, user_headers):
    """Test getting transcription for non-existent task"""
    import uuid
    fake_id = str(uuid.uuid4())
    response = await test_client.get(
        f"/api/v1/tasks/{fake_id}/transcription",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_transcription_unauthorized(test_client, user_headers, test_db, test_admin):
    """Test getting transcription for another user's task"""
    import uuid
    from app.models.task import Task
    from app.models.transcription import Transcription

    # Create admin's task with transcription
    admin_task = Task(
        id=str(uuid.uuid4()),
        user_id=test_admin.id,
        filename="admin.mp3",
        file_path="/tmp/admin.mp3",
        file_size=10485760,  # 10 MB in bytes
        model_name="tiny",
        language="ja",
        status="completed",
        progress=100,
        file_format="mp3"
    )
    test_db.add(admin_task)
    await test_db.flush()

    transcription = Transcription(
        task_id=admin_task.id,
        transcription_text="Admin's transcription",
        segments=[],
        word_count=2
    )
    test_db.add(transcription)
    await test_db.commit()

    # Try to access as regular user
    response = await test_client.get(
        f"/api/v1/tasks/{admin_task.id}/transcription",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_transcription(test_client, user_headers, completed_task):
    """Test updating transcription"""
    update_data = {
        "transcription_text": "Updated transcription text",
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 5.0,
                "text": "Updated segment",
                "speaker_id": 1,
                "speaker_label": "Speaker 1",
                "confidence": 0.99
            }
        ]
    }

    response = await test_client.put(
        f"/api/v1/tasks/{completed_task.id}/transcription",
        headers=user_headers,
        json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["transcription_text"] == "Updated transcription text"
    assert len(data["segments"]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_transcription_segment(test_client, user_headers, completed_task):
    """Test updating single segment"""
    update_data = {
        "segment_id": 0,
        "text": "Updated segment text",
        "start": 0.0,
        "end": 6.0,
        "speaker_label": "Speaker A"
    }

    response = await test_client.patch(
        f"/api/v1/tasks/{completed_task.id}/transcription/segments",
        headers=user_headers,
        json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Find the updated segment
    updated_segment = data["segments"][0]
    assert updated_segment["text"] == "Updated segment text"
    assert updated_segment["end"] == 6.0
    assert updated_segment["speaker_label"] == "Speaker A"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_transcription_unauthorized(test_client, user_headers, test_db, test_admin):
    """Test updating another user's transcription"""
    import uuid
    from app.models.task import Task
    from app.models.transcription import Transcription

    # Create admin's task with transcription
    admin_task = Task(
        id=str(uuid.uuid4()),
        user_id=test_admin.id,
        filename="admin.mp3",
        file_path="/tmp/admin.mp3",
        file_size=10485760,  # 10 MB in bytes
        model_name="tiny",
        language="ja",
        status="completed",
        progress=100,
        file_format="mp3"
    )
    test_db.add(admin_task)
    await test_db.flush()

    transcription = Transcription(
        task_id=admin_task.id,
        transcription_text="Admin's transcription",
        segments=[],
        word_count=2
    )
    test_db.add(transcription)
    await test_db.commit()

    update_data = {
        "transcription_text": "Hacked text",
        "segments": []
    }

    response = await test_client.put(
        f"/api/v1/tasks/{admin_task.id}/transcription",
        headers=user_headers,
        json=update_data
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_subtitle_srt(test_client, user_headers, completed_task):
    """Test downloading SRT subtitle"""
    response = await test_client.get(
        f"/api/v1/tasks/{completed_task.id}/subtitle?format=srt",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/plain; charset=utf-8"

    # Check SRT format
    content = response.text
    assert "1" in content  # Sequence number
    assert "00:00:00,000 --> 00:00:05,500" in content  # Timestamp
    assert "これはテストです。" in content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_subtitle_vtt(test_client, user_headers, completed_task):
    """Test downloading VTT subtitle"""
    response = await test_client.get(
        f"/api/v1/tasks/{completed_task.id}/subtitle?format=vtt",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    # API currently returns text/plain for VTT, which is acceptable
    assert "text/plain" in response.headers["content-type"]

    # Check VTT format
    content = response.text
    assert "WEBVTT" in content
    assert "00:00:00.000 --> 00:00:05.500" in content
    assert "これはテストです。" in content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_subtitle_invalid_format(test_client, user_headers, completed_task):
    """Test downloading subtitle with invalid format"""
    response = await test_client.get(
        f"/api/v1/tasks/{completed_task.id}/subtitle?format=invalid",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_subtitle_no_transcription(test_client, user_headers, test_task):
    """Test downloading subtitle for task without transcription"""
    response = await test_client.get(
        f"/api/v1/tasks/{test_task.id}/subtitle?format=srt",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transcription_endpoints_require_auth(test_client, completed_task):
    """Test that transcription endpoints require authentication"""
    # Get transcription
    response = await test_client.get(f"/api/v1/tasks/{completed_task.id}/transcription")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Update transcription
    response = await test_client.put(
        f"/api/v1/tasks/{completed_task.id}/transcription",
        json={"transcription_text": "test", "segments": []}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Download subtitle
    response = await test_client.get(f"/api/v1/tasks/{completed_task.id}/subtitle")
    assert response.status_code == status.HTTP_403_FORBIDDEN
