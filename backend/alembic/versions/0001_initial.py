"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

season_phase = postgresql.ENUM(
    "construccion", "conflicto", "convergencia", "colapso", name="season_phase"
)
user_role = postgresql.ENUM(
    "mercader", "guardia", "cronista", "explorador", name="user_role"
)


def upgrade() -> None:
    bind = op.get_bind()
    season_phase.create(bind, checkfirst=True)
    user_role.create(bind, checkfirst=True)

    op.create_table(
        "factions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("color", sa.String(16), nullable=False),
    )

    op.create_table(
        "seasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("phase", season_phase, nullable=False, server_default="construccion"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("handle", sa.String(60), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("faction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("factions.id"), nullable=True),
        sa.Column("role", user_role, nullable=True),
        sa.Column("chispas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "world_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("season_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seasons.id"), nullable=False, unique=True),
        sa.Column("poblacion", sa.Integer, nullable=False, server_default="50"),
        sa.Column("comida", sa.Integer, nullable=False, server_default="50"),
        sa.Column("moral", sa.Integer, nullable=False, server_default="50"),
        sa.Column("defensa", sa.Integer, nullable=False, server_default="50"),
        sa.Column("oro", sa.Integer, nullable=False, server_default="50"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("season_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column("question", sa.String(280), nullable=False),
        sa.Column("option_a", sa.String(120), nullable=False),
        sa.Column("option_b", sa.String(120), nullable=False),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("season_id", "day", name="uq_decision_season_day"),
    )

    op.create_table(
        "votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decisions.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("option", sa.String(1), nullable=False),
        sa.Column("weight", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("decision_id", "user_id", name="uq_vote_decision_user"),
    )

    op.create_table(
        "chispa_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("reason", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("chispa_transactions")
    op.drop_table("votes")
    op.drop_table("decisions")
    op.drop_table("world_states")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("seasons")
    op.drop_table("factions")

    bind = op.get_bind()
    user_role.drop(bind, checkfirst=True)
    season_phase.drop(bind, checkfirst=True)
