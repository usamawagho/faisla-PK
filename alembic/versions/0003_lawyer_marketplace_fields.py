"""Add public lawyer marketplace fields.

Revision ID: 0003_marketplace_fields
Revises: 0002_profile_integrity
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_marketplace_fields"
down_revision: Union[str, None] = "0002_profile_integrity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lawyer_profiles",
        sa.Column(
            "years_of_experience",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "lawyer_profiles",
        sa.Column("consultation_fee", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "lawyer_profiles",
        sa.Column(
            "languages",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )
    op.add_column(
        "lawyer_profiles",
        sa.Column("office_address", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lawyer_profiles", "office_address")
    op.drop_column("lawyer_profiles", "languages")
    op.drop_column("lawyer_profiles", "consultation_fee")
    op.drop_column("lawyer_profiles", "years_of_experience")
