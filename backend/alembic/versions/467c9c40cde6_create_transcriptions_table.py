"""create_transcriptions_table

Revision ID: 467c9c40cde6
Revises: 002
Create Date: 2025-10-13 05:04:52.920273

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '467c9c40cde6'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create transcriptions table
    op.create_table(
        'transcriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transcription_text', sa.Text(), nullable=False),
        sa.Column('segments', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('subtitle_path', sa.String(length=500), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('word_count IS NULL OR word_count >= 0', name='transcriptions_word_count_positive'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )

    # Create indexes
    op.create_index('idx_transcriptions_task_id', 'transcriptions', ['task_id'], unique=True)
    op.create_index('idx_transcriptions_created_at', 'transcriptions', [sa.text('created_at DESC')])
    op.create_index('idx_transcriptions_segments_gin', 'transcriptions', ['segments'],
                    postgresql_using='gin', postgresql_ops={'segments': 'jsonb_path_ops'})


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_transcriptions_segments_gin', table_name='transcriptions')
    op.drop_index('idx_transcriptions_created_at', table_name='transcriptions')
    op.drop_index('idx_transcriptions_task_id', table_name='transcriptions')

    # Drop table
    op.drop_table('transcriptions')
