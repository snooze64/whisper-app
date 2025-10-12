"""
Authentication service for LDAP and user management
"""
from datetime import datetime
from typing import Optional
from ldap3 import Server, Connection, ALL, SIMPLE
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.models.user import User
from app.schemas.auth import TokenResponse


class AuthService:
    """Authentication service"""

    # Mock users for development
    MOCK_USERS = {
        "admin": {"password": "admin123", "email": "admin@example.com", "is_admin": True},
        "user1": {"password": "user123", "email": "user1@example.com", "is_admin": False},
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_mock(self, username: str, password: str) -> Optional[dict]:
        """
        Mock authentication for development environment

        Args:
            username: Username
            password: Password

        Returns:
            User data dict if authentication successful, None otherwise
        """
        user_data = self.MOCK_USERS.get(username)
        if user_data and user_data["password"] == password:
            return {
                "username": username,
                "email": user_data["email"],
                "is_admin": user_data["is_admin"]
            }
        return None

    async def authenticate_ldap(self, username: str, password: str) -> bool:
        """
        Authenticate user against LDAP server

        Args:
            username: Username
            password: Password

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Connect to LDAP server
            server = Server(settings.LDAP_SERVER, get_info=ALL)

            # Format user DN
            user_dn = settings.LDAP_USER_DN_TEMPLATE.format(username=username)

            # Attempt to bind with user credentials
            conn = Connection(
                server,
                user=user_dn,
                password=password,
                authentication=SIMPLE,
                auto_bind=True
            )

            # If we get here, authentication was successful
            conn.unbind()
            return True

        except Exception as e:
            # Log error in production
            print(f"LDAP authentication error: {e}")
            return False

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username

        Args:
            username: Username

        Returns:
            User object or None
        """
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def create_user(self, username: str, email: Optional[str] = None, is_admin: bool = False) -> User:
        """
        Create a new user

        Args:
            username: Username
            email: Email address
            is_admin: Admin flag

        Returns:
            Created user object
        """
        user = User(
            username=username,
            email=email,
            is_admin=is_admin,
            created_at=datetime.utcnow()
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_last_login(self, user: User) -> User:
        """
        Update user's last login time

        Args:
            user: User object

        Returns:
            Updated user object
        """
        user.last_login = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, username: str, password: str) -> Optional[TokenResponse]:
        """
        Authenticate user and generate tokens

        Args:
            username: Username
            password: Password

        Returns:
            Token response or None if authentication failed
        """
        # Use mock authentication in development mode
        if settings.USE_MOCK_AUTH:
            mock_user = await self.authenticate_mock(username, password)
            if not mock_user:
                return None

            # Get or create user in database
            user = await self.get_user_by_username(username)
            if not user:
                # Create user on first login with mock data
                user = await self.create_user(
                    username=mock_user["username"],
                    email=mock_user["email"],
                    is_admin=mock_user["is_admin"]
                )
        else:
            # Authenticate against LDAP
            if not await self.authenticate_ldap(username, password):
                return None

            # Get or create user in database
            user = await self.get_user_by_username(username)
            if not user:
                # Create user on first login
                user = await self.create_user(username=username)

        # Update last login
        await self.update_last_login(user)

        # Generate tokens
        token_data = {
            "sub": username,
            "user_id": user.id,
            "is_admin": user.is_admin
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    async def refresh_access_token(self, refresh_token: str) -> Optional[TokenResponse]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Refresh token

        Returns:
            New token response or None if refresh token invalid
        """
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        if not payload:
            return None

        username = payload.get("sub")
        if not username:
            return None

        # Get user from database
        user = await self.get_user_by_username(username)
        if not user:
            return None

        # Generate new tokens
        token_data = {
            "sub": username,
            "user_id": user.id,
            "is_admin": user.is_admin
        }
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
