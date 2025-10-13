"""
Transcription model for storing transcription results
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Transcription(Base):
    """
    Transcription model - stores transcription results

    Relationship: 1:1 with Task
    """
    __tablename__ = "transcriptions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    transcription_text = Column(Text, nullable=False)
    segments = Column(JSONB, nullable=False)
    subtitle_path = Column(String(500), nullable=True)
    word_count = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("word_count IS NULL OR word_count >= 0", name="transcriptions_word_count_positive"),
    )

    # Relationship
    task = relationship("Task", back_populates="transcription")
