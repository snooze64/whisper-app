"""
ProcessingHistory model for storing permanent processing records
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, DECIMAL, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class ProcessingHistory(Base):
    """ProcessingHistory model - permanent record of task processing"""

    __tablename__ = "processing_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    processing_time_seconds = Column(Integer, nullable=False)
    gpu_memory_used_mb = Column(Integer)
    model_name = Column(String(50), nullable=False)
    file_format = Column(String(50), nullable=False)
    file_size_mb = Column(DECIMAL(10, 2), nullable=False)
    success = Column(Boolean, nullable=False)
    error_type = Column(String(100))
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    # Relationships
    task = relationship("Task")
    user = relationship("User")

    # Table arguments for check constraints
    __table_args__ = (
        CheckConstraint('processing_time_seconds >= 0', name='processing_history_time_positive'),
        CheckConstraint('gpu_memory_used_mb IS NULL OR gpu_memory_used_mb > 0', name='processing_history_gpu_positive'),
        CheckConstraint('file_size_mb > 0', name='processing_history_size_positive'),
    )
