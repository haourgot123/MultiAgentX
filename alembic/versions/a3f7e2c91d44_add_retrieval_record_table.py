"""add retrieval_record table

Revision ID: a3f7e2c91d44
Revises: 5b4f4d16c9aa
Create Date: 2026-04-12 04:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f7e2c91d44"
down_revision: Union[str, Sequence[str], None] = "5b4f4d16c9aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create RetrievalRecord table."""
    op.create_table(
        "RetrievalRecord",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.UnicodeText(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.UnicodeText(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("citation_label", sa.UnicodeText(), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("bbox_json", sa.UnicodeText(), nullable=True),
        sa.Column("chunk_text", sa.UnicodeText(), nullable=True),
        sa.Column("relevance_score", sa.UnicodeText(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["Conversation.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["ConversationMessage.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["User.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_RetrievalRecord_id"), "RetrievalRecord", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_RetrievalRecord_conversation_id"),
        "RetrievalRecord",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_RetrievalRecord_message_id"),
        "RetrievalRecord",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_RetrievalRecord_user_id"),
        "RetrievalRecord",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop RetrievalRecord table."""
    op.drop_index(op.f("ix_RetrievalRecord_user_id"), table_name="RetrievalRecord")
    op.drop_index(op.f("ix_RetrievalRecord_message_id"), table_name="RetrievalRecord")
    op.drop_index(
        op.f("ix_RetrievalRecord_conversation_id"), table_name="RetrievalRecord"
    )
    op.drop_index(op.f("ix_RetrievalRecord_id"), table_name="RetrievalRecord")
    op.drop_table("RetrievalRecord")
