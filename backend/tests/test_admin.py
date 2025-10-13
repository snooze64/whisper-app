"""
Test admin API endpoints
"""
import pytest
from fastapi import status


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_dashboard_stats(test_client, admin_headers, test_db, test_user, test_admin):
    """Test getting dashboard statistics"""
    from app.models.task import Task
    from app.models.processing_history import ProcessingHistory
    import uuid

    # Create some tasks and history
    for i in range(5):
        task = Task(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            filename=f"test{i}.mp3",
            file_path=f"/tmp/test{i}.mp3",
            file_size=10485760,  # 10 MB in bytes
            model_name="tiny",
            language="ja",
            status="completed",
            progress=100,
            file_format="mp3"
        )
        test_db.add(task)
        await test_db.flush()

        history = ProcessingHistory(
            task_id=task.id,
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
    await test_db.commit()

    response = await test_client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "total_users" in data
    assert "total_tasks" in data
    assert "active_tasks" in data
    assert "completed_tasks_today" in data
    assert "model_usage" in data
    assert "format_usage" in data
    assert "hourly_stats" in data

    assert data["total_users"] == 2  # test_user + test_admin
    assert data["total_tasks"] >= 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_dashboard_stats_requires_admin(test_client, user_headers):
    """Test that dashboard stats require admin privileges"""
    response = await test_client.get("/api/v1/admin/dashboard", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_system_status(test_client, admin_headers):
    """Test getting system status"""
    response = await test_client.get("/api/v1/admin/system-status", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "gpu_available" in data
    assert "active_workers" in data
    assert "pending_tasks" in data
    assert "processing_tasks" in data

    # GPU info may be None in test environment
    assert isinstance(data["gpu_available"], bool)
    assert isinstance(data["active_workers"], int)
    assert isinstance(data["pending_tasks"], int)
    assert isinstance(data["processing_tasks"], int)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_system_status_requires_admin(test_client, user_headers):
    """Test that system status requires admin privileges"""
    response = await test_client.get("/api/v1/admin/system-status", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_users(test_client, admin_headers, test_user, test_admin):
    """Test getting all users"""
    response = await test_client.get("/api/v1/admin/users", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # API may return list directly or dict with users/total
    if isinstance(data, list):
        users = data
        assert len(users) >= 2
    else:
        assert "users" in data
        assert "total" in data
        users = data["users"]
        assert data["total"] >= 2
        assert len(users) >= 2

    # Check user data
    usernames = [user["username"] for user in users]
    assert "testuser" in usernames
    assert "admin" in usernames


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_users_pagination(test_client, admin_headers, test_db):
    """Test users list pagination"""
    from app.models.user import User

    # Create 15 users
    for i in range(15):
        user = User(
            username=f"user{i}",
            email=f"user{i}@example.com",
            is_admin=False
        )
        test_db.add(user)
    await test_db.commit()

    # Test first page
    response = await test_client.get(
        "/api/v1/admin/users?page=1&page_size=10",
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Handle both response formats
    if isinstance(data, list):
        assert len(data) == 10
    else:
        assert data["total"] >= 15
        assert len(data["users"]) == 10

    # Test second page
    response = await test_client.get(
        "/api/v1/admin/users?page=2&page_size=10",
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Handle both response formats
    if isinstance(data, list):
        assert len(data) >= 5
    else:
        assert len(data["users"]) >= 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_users_requires_admin(test_client, user_headers):
    """Test that users list requires admin privileges"""
    response = await test_client.get("/api/v1/admin/users", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_tasks_admin(test_client, admin_headers, test_task):
    """Test admin getting all tasks"""
    response = await test_client.get("/api/v1/admin/tasks", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "tasks" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_tasks_requires_admin(test_client, user_headers):
    """Test that all tasks endpoint requires admin privileges"""
    response = await test_client.get("/api/v1/admin/tasks", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_overall_stats(test_client, admin_headers, test_processing_history):
    """Test getting overall statistics"""
    response = await test_client.get("/api/v1/admin/stats", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "total_tasks" in data
    assert "successful_tasks" in data
    assert "failed_tasks" in data
    assert "success_rate" in data
    assert "avg_processing_time" in data
    assert "total_file_size" in data

    assert data["total_tasks"] >= 1
    assert data["successful_tasks"] >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_overall_stats_with_days_filter(test_client, admin_headers, test_db, test_user, completed_task):
    """Test overall stats with days filter"""
    from app.models.processing_history import ProcessingHistory
    from datetime import datetime, timedelta

    # Create recent history
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

    # Create old history
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

    response = await test_client.get("/api/v1/admin/stats?days=7", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_tasks"] == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_overall_stats_requires_admin(test_client, user_headers):
    """Test that overall stats require admin privileges"""
    response = await test_client.get("/api/v1/admin/stats", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_admin_endpoints_require_auth(test_client):
    """Test that admin endpoints require authentication"""
    # Dashboard
    response = await test_client.get("/api/v1/admin/dashboard")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # System status
    response = await test_client.get("/api/v1/admin/system-status")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Users
    response = await test_client.get("/api/v1/admin/users")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Tasks
    response = await test_client.get("/api/v1/admin/tasks")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Stats
    response = await test_client.get("/api/v1/admin/stats")
    assert response.status_code == status.HTTP_403_FORBIDDEN
