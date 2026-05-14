"""drop video generation job

Revision ID: b9e4a6d1c2f3
Revises: 7c9d4e2f1a6b
Create Date: 2026-05-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b9e4a6d1c2f3"
down_revision: Union[str, Sequence[str], None] = "7c9d4e2f1a6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('DROP TABLE IF EXISTS "VideoGenerationJob" CASCADE')


def downgrade() -> None:
    pass
