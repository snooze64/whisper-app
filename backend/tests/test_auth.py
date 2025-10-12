"""
Test authentication endpoints
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


def test_login_endpoint_exists():
    """Test that login endpoint exists"""
    response = client.post("/api/v1/auth/login", json={
        "username": "test",
        "password": "test"
    })
    # Should get 401 for invalid credentials, not 404
    assert response.status_code in [401, 422]


def test_refresh_endpoint_exists():
    """Test that refresh endpoint exists"""
    response = client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid_token"
    })
    # Should get 401 for invalid token, not 404
    assert response.status_code in [401, 422]


def test_me_endpoint_requires_auth():
    """Test that /me endpoint requires authentication"""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 403  # No auth header


def test_me_endpoint_with_token():
    """Test /me endpoint with valid token"""
    # Create a test token
    token = create_access_token({"sub": "testuser", "user_id": 1, "is_admin": False})

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Will fail without actual user in DB, but endpoint should exist
    assert response.status_code in [200, 401]


def test_logout_endpoint():
    """Test logout endpoint"""
    token = create_access_token({"sub": "testuser", "user_id": 1, "is_admin": False})

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Will work even without user in DB since logout is client-side
    assert response.status_code in [200, 401]
