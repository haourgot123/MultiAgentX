"""add agent_skill and sandbox_session tables

Revision ID: d8e5a1b3c9f2
Revises: a3f7e2c91d44
Create Date: 2026-04-15 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8e5a1b3c9f2"
down_revision: Union[str, Sequence[str], None] = "a3f7e2c91d44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "AgentSkill",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.UnicodeText(), nullable=False),
        sa.Column("description", sa.UnicodeText(), nullable=True),
        sa.Column("storage_path", sa.UnicodeText(), nullable=False),
        sa.Column("skill_content", sa.UnicodeText(), nullable=True),
        sa.Column("allowed_tools", sa.UnicodeText(), nullable=True),
        sa.Column("file_type", sa.UnicodeText(), nullable=False, server_default="md"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["User.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_AgentSkill_id"), "AgentSkill", ["id"], unique=False)
    op.create_index(op.f("ix_AgentSkill_user_id"), "AgentSkill", ["user_id"], unique=False)

    op.create_table(
        "SandboxSession",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["User.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_skill_id"], ["AgentSkill.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_SandboxSession_id"), "SandboxSession", ["id"], unique=False)
    op.create_index(op.f("ix_SandboxSession_user_id"), "SandboxSession", ["user_id"], unique=False)
    op.create_index(op.f("ix_SandboxSession_sandbox_index"), "SandboxSession", ["sandbox_index"], unique=False)
    op.create_index(op.f("ix_SandboxSession_current_skill_id"), "SandboxSession", ["current_skill_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_SandboxSession_current_skill_id"), table_name="SandboxSession")
    op.drop_index(op.f("ix_SandboxSession_sandbox_index"), table_name="SandboxSession")
    op.drop_index(op.f("ix_SandboxSession_user_id"), table_name="SandboxSession")
    op.drop_index(op.f("ix_SandboxSession_id"), table_name="SandboxSession")
    op.drop_table("SandboxSession")

    op.drop_index(op.f("ix_AgentSkill_user_id"), table_name="AgentSkill")
    op.drop_index(op.f("ix_AgentSkill_id"), table_name="AgentSkill")
    op.drop_table("AgentSkill")