"""
Test processing history API endpoints
"""
import pytest
from fastapi import status
from datetime import datetime, timedelta


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_history_list_empty(test_client, user_headers):
    """Test getting empty history list"""
    response = await test_client.get("/api/v1/history", headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "history" in data
    assert "total" in data
    assert data["total"] == 0
    assert len(data["history"]) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_history_list_with_data(test_client, user_headers, test_processing_history):
    """Test getting history list with data"""
    response = await test_client.get("/api/v1/history", headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert len(data["history"]) == 1
    assert data["history"][0]["id"] == test_processing_history.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_history_list_pagination(test_client, user_headers, test_db, test_user, completed_task):
    """Test history list pagination"""
    from app.models.processing_history import ProcessingHistory

    # Create 15 history records
    for i in range(15):
        history = ProcessingHistory(
            task_id=completed_task.id,
            user_id=test_user.id,
            processing_time_seconds=100 + i,
            gpu_memory_used_mb=8192,
            model_name="tiny",
            file_format="mp3",
            file_size_mb=10.0 + i,
            success=True,
            error_type=None
        )
        test_db.add(history)
    await test_db.commit()

    # Test first page
    response = await test_client.get(
        "/api/v1/history?page=1&page_size=10",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 15
    assert len(data["history"]) == 10
    assert data["page"] == 1
    assert data["page_size"] == 10

    # Test second page
    response = await test_client.get(
        "/api/v1/history?page=2&page_size=10",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["history"]) == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_history_list_filter_success(test_client, user_headers, test_db, test_user, completed_task):
    """Test history list with success filter"""
    from app.models.processing_history import ProcessingHistory

    # Create success and failed history records
    for i in range(3):
        history = ProcessingHistory(
            task_id=completed_task.id,
            user_id=test_user.id,
            processing_time_seconds=100,
            gpu_memory_used_mb=8192,
            model_name="tiny",
            file_format="mp3",
            file_size_mb=10.0,
            success=True,
            error_type=None
        )
        test_db.add(history)

    for i in range(2):
        history = ProcessingHistory(
            task_id=completed_task.id,
            user_id=test_user.id,
            processing_time_seconds=50,
            gpu_memory_used_mb=8192,
            model_name="tiny",
            file_format="mp3",
            file_size_mb=10.0,
            success=False,
            error_type="processing_error"
        )
        test_db.add(history)
    await test_db.commit()

    # Test success filter
    response = await test_client.get(
        "/api/v1/history?success=true",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 3
    for item in data["history"]:
        assert item["success"] is True

    # Test failed filter
    response = await test_client.get(
        "/api/v1/history?success=false",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 2
    for item in data["history"]:
        assert item["success"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_history_list_filter_model(test_client, user_headers, test_db, test_user, completed_task):
    """Test history list with model filter"""
    from app.models.processing_history import ProcessingHistory

    # Create history with different models
    models = ["tiny", "base", "small"]
    for model in models:
        for i in range(2):
            history = ProcessingHistory(
                task_id=completed_task.id,
                user_id=test_user.id,
                processing_time_seconds=100,
                gpu_memory_used_mb=8192,
                model_name=model,
                file_format="mp3",
                file_size_mb=10.0,
                success=True,
                error_type=None
            )
            test_db.add(history)
    await test_db.commit()

    # Test tiny model filter
    response = await test_client.get(
        "/api/v1/history?model_name=tiny",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 2
    for item in data["history"]:
        assert item["model_name"] == "tiny"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_history_detail(test_client, user_headers, test_processing_history):
    """Test getting history detail"""
    response = await test_client.get(
        f"/api/v1/history/{test_processing_history.id}",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_processing_history.id
    assert data["processing_time_seconds"] == test_processing_history.processing_time_seconds
    assert data["model_name"] == test_processing_history.model_name


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_history_detail_not_found(test_client, user_headers):
    """Test getting non-existent history"""
    response = await test_client.get("/api/v1/history/99999", headers=user_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_history_detail_unauthorized(test_client, user_headers, test_db, test_admin, completed_task):
    """Test getting another user's history"""
    from app.models.processing_history import ProcessingHistory

    # Create admin's history
    admin_history = ProcessingHistory(
        task_id=completed_task.id,
        user_id=test_admin.id,
        processing_time_seconds=100,
        gpu_memory_used_mb=8192,
        model_name="tiny",
        file_format="mp3",
        file_size_mb=10.0,
        success=True,
        error_type=None
    )
    test_db.add(admin_history)
    await test_db.commit()
    await test_db.refresh(admin_history)

    # Try to access as regular user
    response = await test_client.get(
        f"/api/v1/history/{admin_history.id}",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_my_stats(test_client, user_headers, test_processing_history):
    """Test getting user statistics"""
    response = await test_client.get("/api/v1/history/stats/me", headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_tasks" in data
    assert "successful_tasks" in data
    assert "failed_tasks" in data
    assert "success_rate" in data
    assert "avg_processing_time" in data
    assert data["total_tasks"] == 1
    assert data["successful_tasks"] == 1
    assert data["success_rate"] == 100.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_my_stats_with_days_filter(test_client, user_headers, test_db, test_user, completed_task):
    """Test getting user statistics with days filter"""
    from app.models.processing_history import ProcessingHistory

    # Create history records with different dates
    # Recent history (within 7 days)
    for i in range(3):
        history = ProcessingHistory(
            task_id=completed_task.id,
            user_id=test_user.id,
            processing_time_seconds=100,
            gpu_memory_used_mb=8192,
            model_name="tiny",
            file_format="mp3",
            file_size_mb=10.0,
            success=True,
            error_type=None,
            created_at=datetime.utcnow() - timedelta(days=i)
        )
        test_db.add(history)

    # Old history (older than 7 days)
    old_history = ProcessingHistory(
        task_id=completed_task.id,
        user_id=test_user.id,
        processing_time_seconds=100,
        gpu_memory_used_mb=8192,
        model_name="tiny",
        file_format="mp3",
        file_size_mb=10.0,
        success=True,
        error_type=None,
        created_at=datetime.utcnow() - timedelta(days=10)
    )
    test_db.add(old_history)
    await test_db.commit()

    # Test with 7 days filter
    response = await test_client.get(
        "/api/v1/history/stats/me?days=7",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_tasks"] == 3  # Only recent history


@pytest.mark.unit
@pytest.mark.asyncio
async def test_history_endpoints_require_auth(test_client):
    """Test that history endpoints require authentication"""
    # List
    response = await test_client.get("/api/v1/history")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Detail
    response = await test_client.get("/api/v1/history/1")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Stats
    response = await test_client.get("/api/v1/history/stats/me")
    assert response.status_code == status.HTTP_403_FORBIDDEN
