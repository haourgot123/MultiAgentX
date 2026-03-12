"""add ingestion columns to file asset

Revision ID: 5b4f4d16c9aa
Revises: 1f9d2b7c4a11
Create Date: 2026-03-12 21:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b4f4d16c9aa"
down_revision: Union[str, Sequence[str], None] = "1f9d2b7c4a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "FileAsset",
        sa.Column(
            "ingestion_status",
            sa.UnicodeText(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "FileAsset",
        sa.Column("ingestion_error", sa.UnicodeText(), nullable=True),
    )
    op.add_column(
        "FileAsset",
        sa.Column(
            "ingested_chunks",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "FileAsset",
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.alter_column("FileAsset", "ingestion_status", server_default=None)
    op.alter_column("FileAsset", "ingested_chunks", server_default=None)


def downgrade() -> None:
    op.drop_column("FileAsset", "ingested_at")
    op.drop_column("FileAsset", "ingested_chunks")
    op.drop_column("FileAsset", "ingestion_error")
    op.drop_column("FileAsset", "ingestion_status")
