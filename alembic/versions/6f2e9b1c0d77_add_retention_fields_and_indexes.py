"""add retention fields and indexes

Revision ID: 6f2e9b1c0d77
Revises: c2f4a9d7e6b1
Create Date: 2026-04-29 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f2e9b1c0d77"
down_revision: Union[str, Sequence[str], None] = "c2f4a9d7e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "FileAsset",
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "FileAsset",
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "Conversation",
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "Conversation",
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "RetrievalRecord",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "AgentSkill",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "AgentSkill",
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "AgentSkill",
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "SkillExecutionArtifact",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "SkillExecutionArtifact",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "SkillExecutionArtifact",
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "SkillExecutionArtifact",
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_FileAsset_user_deleted_updated",
        "FileAsset",
        ["user_id", "deleted_at", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_FileAsset_purge_after",
        "FileAsset",
        ["purge_after"],
        unique=False,
    )
    op.create_index(
        "ix_Conversation_user_deleted_updated",
        "Conversation",
        ["user_id", "deleted_at", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_Conversation_purge_after",
        "Conversation",
        ["purge_after"],
        unique=False,
    )
    op.create_index(
        "ix_RetrievalRecord_user_conversation_message",
        "RetrievalRecord",
        ["user_id", "conversation_id", "message_id"],
        unique=False,
    )
    op.create_index(
        "ix_AgentSkill_user_deleted_created",
        "AgentSkill",
        ["user_id", "deleted_at", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_AgentSkill_purge_after",
        "AgentSkill",
        ["purge_after"],
        unique=False,
    )
    op.create_index(
        "ix_SkillExecutionArtifact_user_deleted_created",
        "SkillExecutionArtifact",
        ["user_id", "deleted_at", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_SkillExecutionArtifact_purge_after",
        "SkillExecutionArtifact",
        ["purge_after"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index(
        "ix_SkillExecutionArtifact_purge_after",
        table_name="SkillExecutionArtifact",
    )
    op.drop_index(
        "ix_SkillExecutionArtifact_user_deleted_created",
        table_name="SkillExecutionArtifact",
    )
    op.drop_index("ix_AgentSkill_purge_after", table_name="AgentSkill")
    op.drop_index("ix_AgentSkill_user_deleted_created", table_name="AgentSkill")
    op.drop_index(
        "ix_RetrievalRecord_user_conversation_message",
        table_name="RetrievalRecord",
    )
    op.drop_index("ix_Conversation_purge_after", table_name="Conversation")
    op.drop_index(
        "ix_Conversation_user_deleted_updated",
        table_name="Conversation",
    )
    op.drop_index("ix_FileAsset_purge_after", table_name="FileAsset")
    op.drop_index("ix_FileAsset_user_deleted_updated", table_name="FileAsset")

    op.drop_column("SkillExecutionArtifact", "purged_at")
    op.drop_column("SkillExecutionArtifact", "purge_after")
    op.drop_column("SkillExecutionArtifact", "deleted_at")
    op.drop_column("SkillExecutionArtifact", "updated_at")
    op.drop_column("AgentSkill", "purged_at")
    op.drop_column("AgentSkill", "purge_after")
    op.drop_column("AgentSkill", "deleted_at")
    op.drop_column("RetrievalRecord", "updated_at")
    op.drop_column("Conversation", "purged_at")
    op.drop_column("Conversation", "purge_after")
    op.drop_column("FileAsset", "purged_at")
    op.drop_column("FileAsset", "purge_after")
