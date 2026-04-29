"""store message blob and drop skill runtime tables

Revision ID: 7c9d4e2f1a6b
Revises: 6f2e9b1c0d77
Create Date: 2026-04-29 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "7c9d4e2f1a6b"
down_revision: Union[str, Sequence[str], None] = "a8c1e3f0b2d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        column["name"] == column_name
        for column in inspect(op.get_bind()).get_columns(table_name)
    )


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        index["name"] == index_name
        for index in inspect(op.get_bind()).get_indexes(table_name)
    )


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_table_if_exists(table_name: str) -> None:
    if _table_exists(table_name):
        op.drop_table(table_name)


def upgrade() -> None:
    if not _column_exists("ConversationMessage", "blob_path"):
        op.add_column("ConversationMessage", sa.Column("blob_path", sa.UnicodeText(), nullable=True))
    if not _column_exists("ConversationMessage", "blob_name"):
        op.add_column("ConversationMessage", sa.Column("blob_name", sa.UnicodeText(), nullable=True))
    if not _column_exists("ConversationMessage", "blob_content_type"):
        op.add_column("ConversationMessage", sa.Column("blob_content_type", sa.UnicodeText(), nullable=True))
    if not _column_exists("ConversationMessage", "blob_size"):
        op.add_column("ConversationMessage", sa.Column("blob_size", sa.BigInteger(), nullable=True))

    if _table_exists("SkillExecutionArtifact"):
        op.execute(
            """
            UPDATE "ConversationMessage"
            SET
                blob_path = (
                    SELECT a.blob_path
                    FROM "SkillExecutionArtifact" a
                    WHERE a.message_id = "ConversationMessage".id
                    ORDER BY a.created_at DESC, a.id DESC
                    LIMIT 1
                ),
                blob_name = (
                    SELECT a.file_name
                    FROM "SkillExecutionArtifact" a
                    WHERE a.message_id = "ConversationMessage".id
                    ORDER BY a.created_at DESC, a.id DESC
                    LIMIT 1
                ),
                blob_content_type = (
                    SELECT a.content_type
                    FROM "SkillExecutionArtifact" a
                    WHERE a.message_id = "ConversationMessage".id
                    ORDER BY a.created_at DESC, a.id DESC
                    LIMIT 1
                ),
                blob_size = (
                    SELECT a.size
                    FROM "SkillExecutionArtifact" a
                    WHERE a.message_id = "ConversationMessage".id
                    ORDER BY a.created_at DESC, a.id DESC
                    LIMIT 1
                )
            WHERE blob_path IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM "SkillExecutionArtifact" a
                  WHERE a.message_id = "ConversationMessage".id
              )
            """
        )

    _drop_index_if_exists("SkillExecutionArtifact", "ix_SkillExecutionArtifact_purge_after")
    _drop_index_if_exists("SkillExecutionArtifact", "ix_SkillExecutionArtifact_user_deleted_created")
    _drop_index_if_exists("SkillExecutionArtifact", op.f("ix_SkillExecutionArtifact_user_id"))
    _drop_index_if_exists("SkillExecutionArtifact", op.f("ix_SkillExecutionArtifact_skill_id"))
    _drop_index_if_exists("SkillExecutionArtifact", op.f("ix_SkillExecutionArtifact_message_id"))
    _drop_index_if_exists("SkillExecutionArtifact", op.f("ix_SkillExecutionArtifact_id"))
    _drop_index_if_exists("SkillExecutionArtifact", op.f("ix_SkillExecutionArtifact_conversation_id"))
    _drop_table_if_exists("SkillExecutionArtifact")

    _drop_index_if_exists("SandboxSession", op.f("ix_SandboxSession_status"))
    _drop_index_if_exists("SandboxSession", op.f("ix_SandboxSession_current_skill_id"))
    _drop_index_if_exists("SandboxSession", op.f("ix_SandboxSession_sandbox_index"))
    _drop_index_if_exists("SandboxSession", op.f("ix_SandboxSession_user_id"))
    _drop_index_if_exists("SandboxSession", op.f("ix_SandboxSession_id"))
    _drop_table_if_exists("SandboxSession")

    _create_index_if_missing(
        "ix_Conversation_user_type_deleted_updated",
        "Conversation",
        ["user_id", "chat_type", "deleted_at", "updated_at"],
    )
    _create_index_if_missing(
        "ix_Conversation_File_file_conversation",
        "Conversation_File",
        ["file_id", "conversation_id"],
    )
    _create_index_if_missing(
        "ix_FileAsset_user_deleted_created",
        "FileAsset",
        ["user_id", "deleted_at", "created_at"],
    )
    _create_index_if_missing(
        "ix_AgentSkill_user_selected_active_deleted",
        "AgentSkill",
        ["user_id", "is_selected", "is_active", "deleted_at"],
    )
    _create_index_if_missing(
        "ix_RetrievalRecord_user_conversation_message_citation",
        "RetrievalRecord",
        ["user_id", "conversation_id", "message_id", "citation_label"],
    )
    _create_index_if_missing(
        "ix_Token_user_type",
        "Token",
        ["user_id", "token_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_Token_user_type", table_name="Token")
    op.drop_index(
        "ix_RetrievalRecord_user_conversation_message_citation",
        table_name="RetrievalRecord",
    )
    op.drop_index(
        "ix_AgentSkill_user_selected_active_deleted",
        table_name="AgentSkill",
    )
    op.drop_index("ix_FileAsset_user_deleted_created", table_name="FileAsset")
    op.drop_index(
        "ix_Conversation_File_file_conversation",
        table_name="Conversation_File",
    )
    op.drop_index(
        "ix_Conversation_user_type_deleted_updated",
        table_name="Conversation",
    )

    op.create_table(
        "SandboxSession",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("sandbox_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.UnicodeText(), nullable=False, server_default="ready"),
        sa.Column("current_skill_id", sa.Integer(), nullable=True),
        sa.Column("task_description", sa.UnicodeText(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cwd", sa.UnicodeText(), nullable=True),
        sa.Column("session_metadata", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["User.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["current_skill_id"], ["AgentSkill.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sandbox_index", name="uq_sandbox_session_index"),
    )
    op.create_index(op.f("ix_SandboxSession_id"), "SandboxSession", ["id"], unique=False)
    op.create_index(op.f("ix_SandboxSession_user_id"), "SandboxSession", ["user_id"], unique=False)
    op.create_index(op.f("ix_SandboxSession_sandbox_index"), "SandboxSession", ["sandbox_index"], unique=False)
    op.create_index(op.f("ix_SandboxSession_current_skill_id"), "SandboxSession", ["current_skill_id"], unique=False)
    op.create_index(op.f("ix_SandboxSession_status"), "SandboxSession", ["status"], unique=False)

    op.create_table(
        "SkillExecutionArtifact",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("sandbox_index", sa.Integer(), nullable=True),
        sa.Column("file_name", sa.UnicodeText(), nullable=False),
        sa.Column("blob_path", sa.UnicodeText(), nullable=False),
        sa.Column("content_type", sa.UnicodeText(), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["Conversation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["ConversationMessage.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["AgentSkill.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["User.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_SkillExecutionArtifact_conversation_id"), "SkillExecutionArtifact", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_SkillExecutionArtifact_id"), "SkillExecutionArtifact", ["id"], unique=False)
    op.create_index(op.f("ix_SkillExecutionArtifact_message_id"), "SkillExecutionArtifact", ["message_id"], unique=False)
    op.create_index(op.f("ix_SkillExecutionArtifact_skill_id"), "SkillExecutionArtifact", ["skill_id"], unique=False)
    op.create_index(op.f("ix_SkillExecutionArtifact_user_id"), "SkillExecutionArtifact", ["user_id"], unique=False)
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

    op.drop_column("ConversationMessage", "blob_size")
    op.drop_column("ConversationMessage", "blob_content_type")
    op.drop_column("ConversationMessage", "blob_name")
    op.drop_column("ConversationMessage", "blob_path")
