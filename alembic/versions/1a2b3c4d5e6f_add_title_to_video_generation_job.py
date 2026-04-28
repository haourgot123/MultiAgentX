"""add_title_to_video_generation_job

Revision ID: 1a2b3c4d5e6f
Revises: 9d8a7f6e5c4b
Create Date: 2026-04-29 02:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "9d8a7f6e5c4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "VideoGenerationJob",
        sa.Column("title", sa.UnicodeText(), nullable=True),
    )
    op.execute(
        """
        UPDATE "VideoGenerationJob"
        SET title = LEFT(prompt, 255)
        WHERE title IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("VideoGenerationJob", "title")
