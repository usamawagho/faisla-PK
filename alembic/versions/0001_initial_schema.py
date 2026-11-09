"""Create the existing users and lawyer profiles schema.

Revision ID: 0001_initial
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role = sa.Enum("CLIENT", "LAWYER", "ADMIN", name="userrole")
verification_status = sa.Enum(
    "PENDING",
    "APPROVED",
    "REJECTED",
    name="verificationstatus",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_id", "users", ["id"], unique=False)

    op.create_table(
        "lawyer_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("license_number", sa.String(), nullable=False),
        sa.Column("bar_council", sa.String(), nullable=False),
        sa.Column("bar_council_number", sa.String(), nullable=False),
        sa.Column("specialization", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("cnic", sa.String(), nullable=False),
        sa.Column("verification_status", verification_status, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bar_council_number"),
        sa.UniqueConstraint("cnic"),
        sa.UniqueConstraint("license_number"),
    )
    op.create_index("ix_lawyer_profiles_id", "lawyer_profiles", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lawyer_profiles_id", table_name="lawyer_profiles")
    op.drop_table("lawyer_profiles")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    verification_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
