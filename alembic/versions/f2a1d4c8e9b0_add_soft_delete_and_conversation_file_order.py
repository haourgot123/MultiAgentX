"""add soft delete and conversation file order

Revision ID: f2a1d4c8e9b0
Revises: b5c7d6528e1c
Create Date: 2026-04-18 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2a1d4c8e9b0"
down_revision: Union[str, Sequence[str], None] = "b5c7d6528e1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "FileAsset",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "Conversation",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "Conversation_File_new",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["Conversation.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["file_id"], ["FileAsset.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "file_id", name="uq_conversation_file_pair"),
    )

    op.execute(
        """
        INSERT INTO "Conversation_File_new" ("conversation_id", "file_id")
        SELECT "conversation_id", "file_id"
        FROM "Conversation_File"
        ORDER BY "conversation_id", "file_id"
        """
    )

    op.drop_table("Conversation_File")
    op.rename_table("Conversation_File_new", "Conversation_File")


def downgrade() -> None:
    op.create_table(
        "Conversation_File_old",
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["Conversation.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["file_id"], ["FileAsset.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("conversation_id", "file_id"),
    )

    op.execute(
        """
        INSERT INTO "Conversation_File_old" ("conversation_id", "file_id")
        SELECT "conversation_id", "file_id"
        FROM "Conversation_File"
        ORDER BY "id"
        """
    )

    op.drop_table("Conversation_File")
    op.rename_table("Conversation_File_old", "Conversation_File")

    op.drop_column("Conversation", "deleted_at")
    op.drop_column("FileAsset", "deleted_at")
