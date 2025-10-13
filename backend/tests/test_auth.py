"""
Test authentication endpoints
"""
import pytest
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_login_endpoint_exists(test_client):
    """Test that login endpoint exists"""
    response = await test_client.post("/api/v1/auth/login", json={
        "username": "test",
        "password": "test"
    })
    # Should get 401 for invalid credentials, not 404
    assert response.status_code in [401, 422]


@pytest.mark.asyncio
async def test_refresh_endpoint_exists(test_client):
    """Test that refresh endpoint exists"""
    response = await test_client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid_token"
    })
    # Should get 401 for invalid token, not 404
    assert response.status_code in [401, 422]


@pytest.mark.asyncio
async def test_me_endpoint_requires_auth(test_client):
    """Test that /me endpoint requires authentication"""
    response = await test_client.get("/api/v1/auth/me")
    assert response.status_code == 403  # No auth header


@pytest.mark.asyncio
async def test_me_endpoint_with_token(test_client, test_user):
    """Test /me endpoint with valid token"""
    # Create a test token
    token = create_access_token({"sub": test_user.username, "user_id": test_user.id, "is_admin": False})

    response = await test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Should work with actual user in DB
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logout_endpoint(test_client, test_user):
    """Test logout endpoint"""
    token = create_access_token({"sub": test_user.username, "user_id": test_user.id, "is_admin": False})

    response = await test_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Will work even without user in DB since logout is client-side
    assert response.status_code in [200, 401]
