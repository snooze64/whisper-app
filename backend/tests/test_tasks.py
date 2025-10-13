"""
Test task API endpoints
"""
import pytest
from fastapi import status


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tasks_list_empty(test_client, user_headers):
    """Test getting empty tasks list"""
    response = await test_client.get("/api/v1/tasks", headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "tasks" in data
    assert "total" in data
    assert data["total"] == 0
    assert len(data["tasks"]) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tasks_list_with_tasks(test_client, user_headers, test_task):
    """Test getting tasks list with tasks"""
    response = await test_client.get("/api/v1/tasks", headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["id"] == str(test_task.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tasks_list_pagination(test_client, user_headers, test_db, test_user):
    """Test tasks list pagination"""
    import uuid
    from app.models.task import Task

    # Create 15 tasks
    for i in range(15):
        task = Task(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            filename=f"test{i}.mp3",
            file_path=f"/tmp/test{i}.mp3",
            file_size=10485760,  # 10 MB in bytes
            model_name="tiny",
            language="ja",
            status="pending",
            progress=0,
            file_format="mp3"
        )
        test_db.add(task)
    await test_db.commit()

    # Test first page
    response = await test_client.get(
        "/api/v1/tasks?page=1&page_size=10",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 15
    assert len(data["tasks"]) == 10
    assert data["page"] == 1
    assert data["page_size"] == 10

    # Test second page
    response = await test_client.get(
        "/api/v1/tasks?page=2&page_size=10",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["tasks"]) == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tasks_list_status_filter(test_client, user_headers, test_db, test_user):
    """Test tasks list with status filter"""
    import uuid
    from app.models.task import Task

    # Create tasks with different statuses
    statuses = ["pending", "processing", "completed", "failed"]
    for status_val in statuses:
        for i in range(2):
            task = Task(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                filename=f"{status_val}{i}.mp3",
                file_path=f"/tmp/{status_val}{i}.mp3",
                file_size=10485760,  # 10 MB in bytes
                model_name="tiny",
                language="ja",
                status=status_val,
                progress=0 if status_val == "pending" else 100,
                file_format="mp3"
            )
            test_db.add(task)
    await test_db.commit()

    # Test completed filter
    response = await test_client.get(
        "/api/v1/tasks?status=completed",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 2
    for task in data["tasks"]:
        assert task["status"] == "completed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_detail(test_client, user_headers, test_task):
    """Test getting task detail"""
    response = await test_client.get(
        f"/api/v1/tasks/{test_task.id}",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(test_task.id)
    assert data["model_name"] == test_task.model_name
    assert data["status"] == test_task.status


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_detail_not_found(test_client, user_headers):
    """Test getting non-existent task"""
    import uuid
    fake_id = str(uuid.uuid4())
    response = await test_client.get(
        f"/api/v1/tasks/{fake_id}",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_detail_unauthorized(test_client, user_headers, test_task, test_db, test_admin):
    """Test getting another user's task (should fail for non-admin)"""
    # Create task owned by admin
    import uuid
    from app.models.task import Task

    admin_task = Task(
        id=str(uuid.uuid4()),
        user_id=test_admin.id,
        filename="admin.mp3",
        file_path="/tmp/admin.mp3",
        file_size=10485760,  # 10 MB in bytes
        model_name="tiny",
        language="ja",
        status="pending",
        progress=0,
        file_format="mp3"
    )
    test_db.add(admin_task)
    await test_db.commit()

    # Try to access as regular user
    response = await test_client.get(
        f"/api/v1/tasks/{admin_task.id}",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_detail_admin_can_access_any(test_client, admin_headers, test_task):
    """Test admin can access any user's task"""
    response = await test_client.get(
        f"/api/v1/tasks/{test_task.id}",
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_status(test_client, user_headers, test_task):
    """Test getting task status"""
    response = await test_client.get(
        f"/api/v1/tasks/{test_task.id}/status",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "progress" in data
    assert data["status"] == test_task.status
    assert data["progress"] == test_task.progress


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_task(test_client, user_headers, test_task):
    """Test deleting task"""
    response = await test_client.delete(
        f"/api/v1/tasks/{test_task.id}",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify task is deleted
    response = await test_client.get(
        f"/api/v1/tasks/{test_task.id}",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_task_unauthorized(test_client, user_headers, test_db, test_admin):
    """Test deleting another user's task (should fail for non-admin)"""
    import uuid
    from app.models.task import Task

    admin_task = Task(
        id=str(uuid.uuid4()),
        user_id=test_admin.id,
        filename="admin.mp3",
        file_path="/tmp/admin.mp3",
        file_size=10485760,  # 10 MB in bytes
        model_name="tiny",
        language="ja",
        status="pending",
        progress=0,
        file_format="mp3"
    )
    test_db.add(admin_task)
    await test_db.commit()

    response = await test_client.delete(
        f"/api/v1/tasks/{admin_task.id}",
        headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_task_admin_can_delete_any(test_client, admin_headers, test_task):
    """Test admin can delete any user's task"""
    response = await test_client.delete(
        f"/api/v1/tasks/{test_task.id}",
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tasks_require_authentication(test_client):
    """Test that tasks endpoints require authentication"""
    # List
    response = await test_client.get("/api/v1/tasks")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Detail
    import uuid
    fake_id = str(uuid.uuid4())
    response = await test_client.get(f"/api/v1/tasks/{fake_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Delete
    response = await test_client.delete(f"/api/v1/tasks/{fake_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN
