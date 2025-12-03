"""add confidence column to parking records

Revision ID: 7d2a5e9b4f1c
Revises: 109c3ea32a1b
Create Date: 2025-11-28 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7d2a5e9b4f1c"
down_revision: Union[str, Sequence[str], None] = "109c3ea32a1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("parking_records", sa.Column("confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("parking_records", "confidence")


