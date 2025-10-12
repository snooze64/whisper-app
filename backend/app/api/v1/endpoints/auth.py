"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user, get_current_active_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, TokenRefreshRequest
from app.schemas.user import User as UserSchema
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with username and password (LDAP authentication)

    - **username**: LDAP username
    - **password**: LDAP password

    Returns:
    - **access_token**: JWT access token (15 minutes)
    - **refresh_token**: JWT refresh token (7 days)
    """
    auth_service = AuthService(db)
    token_response = await auth_service.login(
        username=login_data.username,
        password=login_data.password
    )

    if not token_response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token

    - **refresh_token**: Valid refresh token

    Returns:
    - **access_token**: New JWT access token
    - **refresh_token**: New JWT refresh token
    """
    auth_service = AuthService(db)
    token_response = await auth_service.refresh_access_token(
        refresh_token=refresh_data.refresh_token
    )

    if not token_response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_response


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout (client-side token deletion)

    This endpoint exists for consistency but the actual logout
    is handled client-side by deleting the tokens.

    Returns:
    - Success message
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information

    Requires valid access token in Authorization header.

    Returns:
    - Current user information
    """
    return current_user
