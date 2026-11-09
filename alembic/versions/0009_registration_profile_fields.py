"""Store additional registration profile fields.

Revision ID: 0009_registration_profile_fields
Revises: 0008_refresh_sessions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_registration_profile_fields"
down_revision: Union[str, None] = "0008_refresh_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=200), nullable=True))
    op.add_column("users", sa.Column("cnic", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("address", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "address")
    op.drop_column("users", "city")
    op.drop_column("users", "cnic")
    op.drop_column("users", "full_name")
