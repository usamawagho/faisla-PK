"""Add legal case management, notes, and status audit history.

Revision ID: 0005_case_management
Revises: 0004_appointments
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_case_management"
down_revision: Union[str, None] = "0004_appointments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


case_status = sa.Enum(
    "OPEN",
    "IN_PROGRESS",
    "WAITING_CLIENT",
    "ON_HOLD",
    "CLOSED",
    name="casestatus",
)
case_priority = sa.Enum(
    "LOW",
    "MEDIUM",
    "HIGH",
    "URGENT",
    name="casepriority",
)
uuid_type = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("lawyer_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=10000), nullable=False),
        sa.Column("case_type", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            case_status,
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column(
            "priority",
            case_priority,
            server_default="MEDIUM",
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
            name="ck_cases_distinct_client_lawyer",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["lawyer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cases_client_id", "cases", ["client_id"])
    op.create_index("ix_cases_lawyer_id", "cases", ["lawyer_id"])
    op.create_index("ix_cases_status", "cases", ["status"])

    op.create_table(
        "case_notes",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_id", uuid_type, nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=10000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_notes_case_id", "case_notes", ["case_id"])
    op.create_index("ix_case_notes_author_id", "case_notes", ["author_id"])

    op.create_table(
        "case_status_history",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_id", uuid_type, nullable=False),
        sa.Column("changed_by_id", sa.Integer(), nullable=False),
        sa.Column("previous_status", case_status, nullable=True),
        sa.Column("new_status", case_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_case_status_history_case_id",
        "case_status_history",
        ["case_id"],
    )
    op.create_index(
        "ix_case_status_history_changed_by_id",
        "case_status_history",
        ["changed_by_id"],
    )
    op.execute(
        """
        CREATE FUNCTION prevent_case_audit_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'case notes and status history are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER case_notes_immutable
        BEFORE UPDATE OR DELETE ON case_notes
        FOR EACH ROW EXECUTE FUNCTION prevent_case_audit_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER case_status_history_immutable
        BEFORE UPDATE OR DELETE ON case_status_history
        FOR EACH ROW EXECUTE FUNCTION prevent_case_audit_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER case_status_history_immutable ON case_status_history")
    op.execute("DROP TRIGGER case_notes_immutable ON case_notes")
    op.execute("DROP FUNCTION prevent_case_audit_mutation()")
    op.drop_index(
        "ix_case_status_history_changed_by_id",
        table_name="case_status_history",
    )
    op.drop_index(
        "ix_case_status_history_case_id",
        table_name="case_status_history",
    )
    op.drop_table("case_status_history")
    op.drop_index("ix_case_notes_author_id", table_name="case_notes")
    op.drop_index("ix_case_notes_case_id", table_name="case_notes")
    op.drop_table("case_notes")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_index("ix_cases_lawyer_id", table_name="cases")
    op.drop_index("ix_cases_client_id", table_name="cases")
    op.drop_table("cases")
    case_priority.drop(op.get_bind(), checkfirst=True)
    case_status.drop(op.get_bind(), checkfirst=True)
