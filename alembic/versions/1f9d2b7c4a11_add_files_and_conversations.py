"""add files and conversations

Revision ID: 1f9d2b7c4a11
Revises: 80b311e3fae6
Create Date: 2026-03-12 19:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f9d2b7c4a11"
down_revision: Union[str, Sequence[str], None] = "80b311e3fae6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "FileAsset",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.UnicodeText(), nullable=False),
        sa.Column("storage_path", sa.UnicodeText(), nullable=False),
        sa.Column("mime_type", sa.UnicodeText(), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["User.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_FileAsset_id"), "FileAsset", ["id"], unique=False)
    op.create_index(op.f("ix_FileAsset_user_id"), "FileAsset", ["user_id"], unique=False)

    op.create_table(
        "Conversation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.UnicodeText(), nullable=False),
        sa.Column("chat_type", sa.UnicodeText(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["User.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_Conversation_id"), "Conversation", ["id"], unique=False)
    op.create_index(
        op.f("ix_Conversation_user_id"), "Conversation", ["user_id"], unique=False
    )

    op.create_table(
        "Conversation_File",
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["Conversation.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["file_id"], ["FileAsset.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("conversation_id", "file_id"),
    )

    op.create_table(
        "ConversationMessage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.UnicodeText(), nullable=False),
        sa.Column("content", sa.UnicodeText(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["Conversation.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ConversationMessage_conversation_id"),
        "ConversationMessage",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ConversationMessage_id"), "ConversationMessage", ["id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_ConversationMessage_id"), table_name="ConversationMessage")
    op.drop_index(
        op.f("ix_ConversationMessage_conversation_id"), table_name="ConversationMessage"
    )
    op.drop_table("ConversationMessage")
    op.drop_table("Conversation_File")
    op.drop_index(op.f("ix_Conversation_user_id"), table_name="Conversation")
    op.drop_index(op.f("ix_Conversation_id"), table_name="Conversation")
    op.drop_table("Conversation")
    op.drop_index(op.f("ix_FileAsset_user_id"), table_name="FileAsset")
    op.drop_index(op.f("ix_FileAsset_id"), table_name="FileAsset")
    op.drop_table("FileAsset")
