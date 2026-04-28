"""add_video_generation_job

Revision ID: 9d8a7f6e5c4b
Revises: c2f4a9d7e6b1
Create Date: 2026-04-28 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d8a7f6e5c4b"
down_revision: Union[str, Sequence[str], None] = "c2f4a9d7e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "VideoGenerationJob",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.UnicodeText(), nullable=False),
        sa.Column("style", sa.UnicodeText(), nullable=False),
        sa.Column("aspect_ratio", sa.UnicodeText(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("fps", sa.Integer(), nullable=False),
        sa.Column("web_search_enabled", sa.Boolean(), nullable=False),
        sa.Column("status", sa.UnicodeText(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("storyboard_json", sa.JSON(), nullable=True),
        sa.Column("sources_json", sa.JSON(), nullable=True),
        sa.Column("video_blob_path", sa.UnicodeText(), nullable=True),
        sa.Column("thumbnail_blob_path", sa.UnicodeText(), nullable=True),
        sa.Column("error_message", sa.UnicodeText(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["User.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_VideoGenerationJob_id"),
        "VideoGenerationJob",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_VideoGenerationJob_status"),
        "VideoGenerationJob",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_VideoGenerationJob_user_id"),
        "VideoGenerationJob",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_VideoGenerationJob_user_id"), table_name="VideoGenerationJob")
    op.drop_index(op.f("ix_VideoGenerationJob_status"), table_name="VideoGenerationJob")
    op.drop_index(op.f("ix_VideoGenerationJob_id"), table_name="VideoGenerationJob")
    op.drop_table("VideoGenerationJob")
