"""bridge drifted local schema

Revision ID: a8c1e3f0b2d9
Revises: 6f2e9b1c0d77
Create Date: 2026-04-29 16:20:00.000000

"""
from typing import Sequence, Union


revision: str = "a8c1e3f0b2d9"
down_revision: Union[str, Sequence[str], None] = "6f2e9b1c0d77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op bridge for databases already stamped with this missing revision."""


def downgrade() -> None:
    """No-op bridge for databases already stamped with this missing revision."""
