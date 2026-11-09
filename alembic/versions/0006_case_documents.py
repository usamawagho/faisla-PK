"""Add secure case document metadata.

Revision ID: 0006_case_documents
Revises: 0005_case_management
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_case_documents"
down_revision: Union[str, None] = "0005_case_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


document_type = sa.Enum(
    "CONTRACT",
    "EVIDENCE",
    "COURT_ORDER",
    "AGREEMENT",
    "ID_DOCUMENT",
    "OTHER",
    name="documenttype",
)


def upgrade() -> None:
    op.create_table(
        "case_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("original_file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=127), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_url", sa.String(length=2048), nullable=False),
        sa.Column("storage_public_id", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "file_size > 0 AND file_size <= 10485760",
            name="ck_case_documents_file_size",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_public_id"),
    )
    op.create_index("ix_case_documents_case_id", "case_documents", ["case_id"])
    op.create_index(
        "ix_case_documents_uploaded_by",
        "case_documents",
        ["uploaded_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_case_documents_uploaded_by", table_name="case_documents")
    op.drop_index("ix_case_documents_case_id", table_name="case_documents")
    op.drop_table("case_documents")
    document_type.drop(op.get_bind(), checkfirst=True)
