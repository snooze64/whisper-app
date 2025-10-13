"""
Task model for transcription tasks
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, BigInteger, TIMESTAMP, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.session import Base


class Task(Base):
    """Task model"""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_format = Column(String(50), nullable=False)
    model_name = Column(String(50), nullable=False)
    language = Column(String(10), nullable=False, default="ja")
    num_speakers = Column(Integer)
    status = Column(String(50), nullable=False, default="pending")
    progress = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    error_message = Column(Text)

    # Relationships
    user = relationship("User", back_populates="tasks")
    transcription = relationship("Transcription", back_populates="task", uselist=False, cascade="all, delete-orphan")
