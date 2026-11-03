"""identity and anti-abuse: handle verification and reports

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tipos declarados a mano: se crean explícitamente y las columnas los referencian
# con create_type=False para que SQLAlchemy no intente crearlos dos veces.
handle_verification_status = postgresql.ENUM(
    "none", "pending", "verified", "rejected",
    name="handle_verification_status",
    create_type=False,
)
report_reason = postgresql.ENUM(
    "bot", "suplantacion", "abuso", "otro",
    name="report_reason",
    create_type=False,
)
report_status = postgresql.ENUM(
    "open", "reviewed", "dismissed",
    name="report_status",
    create_type=False,
)
ENUMS = (handle_verification_status, report_reason, report_status)


def _add_handle_verification_columns() -> None:
    op.add_column(
        "users",
        sa.Column(
            "handle_verification_status",
            handle_verification_status,
            nullable=False,
            server_default=sa.text("'none'::handle_verification_status"),
        ),
    )
    op.add_column("users", sa.Column("handle_verification_code", sa.String(32), nullable=True))
    op.add_column(
        "users", sa.Column("handle_verification_requested_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users", sa.Column("handle_verification_reviewed_at", sa.DateTime(timezone=True), nullable=True)
    )


def _create_reports_table() -> None:
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reported_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", report_reason, nullable=False),
        sa.Column("details", sa.String(500), nullable=True),
        sa.Column(
            "status", report_status, nullable=False, server_default=sa.text("'open'::report_status")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("reporter_id <> reported_user_id", name="ck_report_not_self"),
    )
    op.create_index("ix_reports_reported_user_id", "reports", ["reported_user_id"])
    op.create_index(
        "uq_reports_open_pair",
        "reports",
        ["reporter_id", "reported_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in ENUMS:
        enum_type.create(bind, checkfirst=True)
    _add_handle_verification_columns()
    _create_reports_table()


def downgrade() -> None:
    op.drop_index("uq_reports_open_pair", table_name="reports")
    op.drop_index("ix_reports_reported_user_id", table_name="reports")
    op.drop_table("reports")
    for column in (
        "handle_verification_reviewed_at",
        "handle_verification_requested_at",
        "handle_verification_code",
        "handle_verification_status",
    ):
        op.drop_column("users", column)
    bind = op.get_bind()
    for enum_type in reversed(ENUMS):
        enum_type.drop(bind, checkfirst=True)
