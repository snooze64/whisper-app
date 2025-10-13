"""
User model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    """User model for authentication and authorization"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    is_admin = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp()
    )
    last_login = Column(TIMESTAMP, nullable=True)

    __table_args__ = (
        CheckConstraint("char_length(username) >= 3", name="users_username_length"),
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="users_email_format"
        ),
    )

    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', is_admin={self.is_admin})>"
