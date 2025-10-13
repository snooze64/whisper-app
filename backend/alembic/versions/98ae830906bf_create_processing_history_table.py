"""create processing_history table

Revision ID: 98ae830906bf
Revises: 467c9c40cde6
Create Date: 2025-10-13 07:57:08.747222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '98ae830906bf'
down_revision: Union[str, None] = '467c9c40cde6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'processing_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('processing_time_seconds', sa.Integer(), nullable=False),
        sa.Column('gpu_memory_used_mb', sa.Integer(), nullable=True),
        sa.Column('model_name', sa.String(50), nullable=False),
        sa.Column('file_format', sa.String(50), nullable=False),
        sa.Column('file_size_mb', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint('processing_time_seconds >= 0', name='processing_history_time_positive'),
        sa.CheckConstraint('gpu_memory_used_mb IS NULL OR gpu_memory_used_mb > 0', name='processing_history_gpu_positive'),
        sa.CheckConstraint('file_size_mb > 0', name='processing_history_size_positive'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_processing_history_user_id', 'processing_history', ['user_id'])
    op.create_index('idx_processing_history_task_id', 'processing_history', ['task_id'])
    op.create_index('idx_processing_history_created_at', 'processing_history', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_processing_history_success', 'processing_history', ['success'])
    op.create_index('idx_processing_history_model', 'processing_history', ['model_name'])


def downgrade() -> None:
    op.drop_index('idx_processing_history_model', table_name='processing_history')
    op.drop_index('idx_processing_history_success', table_name='processing_history')
    op.drop_index('idx_processing_history_created_at', table_name='processing_history')
    op.drop_index('idx_processing_history_task_id', table_name='processing_history')
    op.drop_index('idx_processing_history_user_id', table_name='processing_history')
    op.drop_table('processing_history')
