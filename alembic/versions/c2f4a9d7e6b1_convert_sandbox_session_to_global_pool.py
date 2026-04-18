"""convert sandbox session to global pool

Revision ID: c2f4a9d7e6b1
Revises: f2a1d4c8e9b0
Create Date: 2026-04-18 17:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2f4a9d7e6b1"
down_revision: Union[str, Sequence[str], None] = "f2a1d4c8e9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sandbox sessions are operational state only, so reset them while migrating
    # from per-user slots to a global pool schema.
    op.drop_index(op.f("ix_SandboxSession_current_skill_id"), table_name="SandboxSession")
    op.drop_index(op.f("ix_SandboxSession_sandbox_index"), table_name="SandboxSession")
    op.drop_index(op.f("ix_SandboxSession_user_id"), table_name="SandboxSession")
    op.drop_index(op.f("ix_SandboxSession_id"), table_name="SandboxSession")
    op.drop_table("SandboxSession")

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


def downgrade() -> None:
    op.drop_index(op.f("ix_SandboxSession_status"), table_name="SandboxSession")
    op.drop_index(op.f("ix_SandboxSession_current_skill_id"), table_name="SandboxSession")
    op.drop_index(op.f("ix_SandboxSession_sandbox_index"), table_name="SandboxSession")
    op.drop_index(op.f("ix_SandboxSession_user_id"), table_name="SandboxSession")
    op.drop_index(op.f("ix_SandboxSession_id"), table_name="SandboxSession")
    op.drop_table("SandboxSession")

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
