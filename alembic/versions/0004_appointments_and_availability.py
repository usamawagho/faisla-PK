"""Create lawyer availability and appointment tables.

Revision ID: 0004_appointments
Revises: 0003_marketplace_fields
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_appointments"
down_revision: Union[str, None] = "0003_marketplace_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


appointment_status = sa.Enum(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "COMPLETED",
    "CANCELLED",
    name="appointmentstatus",
)
consultation_type = sa.Enum(
    "ONLINE",
    "IN_PERSON",
    name="consultationtype",
)
uuid_type = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "lawyer_availabilities",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("lawyer_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6",
            name="ck_lawyer_availability_day_of_week",
        ),
        sa.CheckConstraint(
            "start_time < end_time",
            name="ck_lawyer_availability_time_range",
        ),
        sa.ForeignKeyConstraint(["lawyer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lawyer_availabilities_lawyer_id",
        "lawyer_availabilities",
        ["lawyer_id"],
    )

    op.create_table(
        "appointments",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("lawyer_id", sa.Integer(), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("appointment_time", sa.Time(), nullable=False),
        sa.Column("consultation_type", consultation_type, nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column(
            "status",
            appointment_status,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "client_id <> lawyer_id",
            name="ck_appointment_distinct_client_lawyer",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["lawyer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointments_client_id", "appointments", ["client_id"])
    op.create_index("ix_appointments_lawyer_id", "appointments", ["lawyer_id"])
    op.create_index("ix_appointments_status", "appointments", ["status"])
    op.create_index(
        "ix_appointments_lawyer_schedule",
        "appointments",
        ["lawyer_id", "appointment_date", "appointment_time"],
    )
    op.create_index(
        "ix_appointments_client_schedule",
        "appointments",
        ["client_id", "appointment_date", "appointment_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_appointments_client_schedule", table_name="appointments")
    op.drop_index("ix_appointments_lawyer_schedule", table_name="appointments")
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_lawyer_id", table_name="appointments")
    op.drop_index("ix_appointments_client_id", table_name="appointments")
    op.drop_table("appointments")
    op.drop_index(
        "ix_lawyer_availabilities_lawyer_id",
        table_name="lawyer_availabilities",
    )
    op.drop_table("lawyer_availabilities")
    appointment_status.drop(op.get_bind(), checkfirst=True)
    consultation_type.drop(op.get_bind(), checkfirst=True)
