"""Enforce one profile per lawyer and require active state.

Revision ID: 0002_profile_integrity
Revises: 0001_initial
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_profile_integrity"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            "SELECT user_id FROM lawyer_profiles "
            "GROUP BY user_id HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicates is not None:
        raise RuntimeError(
            "Cannot enforce one lawyer profile per user: duplicate user_id values exist"
        )

    bind.execute(sa.text("UPDATE users SET is_active = TRUE WHERE is_active IS NULL"))
    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    op.create_unique_constraint(
        "uq_lawyer_profiles_user_id",
        "lawyer_profiles",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_lawyer_profiles_user_id",
        "lawyer_profiles",
        type_="unique",
    )
    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )
