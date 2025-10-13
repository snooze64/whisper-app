"""add_performance_indexes

Revision ID: a7daa58c33b9
Revises: 98ae830906bf
Create Date: 2025-10-13 09:21:13.302326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7daa58c33b9'
down_revision: Union[str, None] = '98ae830906bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite index for tasks queries (user's tasks sorted by status and date)
    op.create_index(
        'idx_tasks_user_status_created',
        'tasks',
        ['user_id', 'status', 'created_at'],
        unique=False
    )

    # Add composite index for processing_history stats queries
    op.create_index(
        'idx_processing_history_created_success',
        'processing_history',
        ['created_at', 'success'],
        unique=False
    )

    # Add composite index for user-specific processing history queries
    op.create_index(
        'idx_processing_history_user_created',
        'processing_history',
        ['user_id', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('idx_processing_history_user_created', table_name='processing_history')
    op.drop_index('idx_processing_history_created_success', table_name='processing_history')
    op.drop_index('idx_tasks_user_status_created', table_name='tasks')
