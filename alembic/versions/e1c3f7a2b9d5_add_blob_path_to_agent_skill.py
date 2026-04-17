"""add blob_path to agent_skill table

Revision ID: e1c3f7a2b9d5
Revises: d8e5a1b3c9f2
Create Date: 2026-04-17 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1c3f7a2b9d5"
down_revision: Union[str, Sequence[str], None] = "d8e5a1b3c9f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "AgentSkill",
        sa.Column("blob_path", sa.UnicodeText(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("AgentSkill", "blob_path")
