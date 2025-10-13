"""
Test main FastAPI application
"""
import pytest


@pytest.mark.asyncio
async def test_root_endpoint(test_client):
    """Test root endpoint"""
    response = await test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["message"] == "Whisper Transcription API"


@pytest.mark.asyncio
async def test_health_check(test_client):
    """Test health check endpoint"""
    response = await test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "whisper-api"


@pytest.mark.asyncio
async def test_docs_available(test_client):
    """Test that API docs are available"""
    response = await test_client.get("/api/docs")
    assert response.status_code == 200
