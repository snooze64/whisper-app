"""
User schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=255)
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    """Schema for creating a user"""
    is_admin: bool = False


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    is_admin: Optional[bool] = None


class UserInDB(UserBase):
    """User schema with database fields"""
    id: int
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class User(UserInDB):
    """Public user schema"""
    pass
