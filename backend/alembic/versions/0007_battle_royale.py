"""La Última Luz: events, champions, duels, tactic votes and sponsorships

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tipos declarados a mano (create_type=False): se crean explícitamente una sola vez.
br_event_status = postgresql.ENUM("active", "finished", "sealed", name="br_event_status", create_type=False)
br_tactic = postgresql.ENUM("ataque", "defensa", "astucia", name="br_tactic", create_type=False)
br_seal = postgresql.ENUM("abundancia", "muralla", "oro", "eco", "cuna", name="br_seal", create_type=False)
ENUMS = (br_event_status, br_tactic, br_seal)

UUID = postgresql.UUID(as_uuid=True)


def _create_events() -> None:
    op.create_table(
        "br_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("season_id", UUID, sa.ForeignKey("seasons.id"), nullable=False, unique=True),
        sa.Column("status", br_event_status, nullable=False, server_default=sa.text("'active'::br_event_status")),
        sa.Column("round_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("fallen_zones", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("winner_faction_id", UUID, sa.ForeignKey("factions.id"), nullable=True),
        sa.Column("seal_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seal", br_seal, nullable=True),
        sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sealed_by_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("next_season_id", UUID, sa.ForeignKey("seasons.id"), nullable=True),
    )


def _create_champions() -> None:
    op.create_table(
        "br_champions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("event_id", UUID, sa.ForeignKey("br_events.id"), nullable=False),
        sa.Column("faction_id", UUID, sa.ForeignKey("factions.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("wounds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("eliminated_round", sa.Integer, nullable=True),
        sa.UniqueConstraint("event_id", "faction_id", name="uq_champion_event_faction"),
        sa.CheckConstraint("wounds >= 0", name="ck_champion_wounds_non_negative"),
    )


def _create_duels() -> None:
    op.create_table(
        "br_duels",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("event_id", UUID, sa.ForeignKey("br_events.id"), nullable=False),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("zone", sa.String(32), nullable=False),
        sa.Column("resolves_on", sa.Date, nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wounded_champion_id", UUID, sa.ForeignKey("br_champions.id"), nullable=True),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.UniqueConstraint("event_id", "round_number", name="uq_duel_event_round"),
    )


def _create_tactic_votes() -> None:
    op.create_table(
        "br_tactic_votes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("duel_id", UUID, sa.ForeignKey("br_duels.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("faction_id", UUID, sa.ForeignKey("factions.id"), nullable=False),
        sa.Column("tactic", br_tactic, nullable=False),
        sa.Column("chispas_spent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("weight", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("duel_id", "user_id", name="uq_tactic_vote_duel_user"),
        sa.CheckConstraint("chispas_spent >= 0", name="ck_tactic_vote_chispas_non_negative"),
        sa.CheckConstraint("weight >= 1", name="ck_tactic_vote_weight_positive"),
    )
    op.create_index("ix_br_tactic_votes_duel_faction", "br_tactic_votes", ["duel_id", "faction_id"])


def _create_sponsorships() -> None:
    op.create_table(
        "sponsorships",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("season_id", UUID, sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("sponsor_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("faction_id", UUID, sa.ForeignKey("factions.id"), nullable=False),
        sa.Column("chispas", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sponsor_id <> recipient_id", name="ck_sponsorship_not_self"),
        sa.CheckConstraint("chispas >= 1", name="ck_sponsorship_chispas_positive"),
    )
    op.create_index("ix_sponsorships_season_recipient", "sponsorships", ["season_id", "recipient_id"])


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in ENUMS:
        enum_type.create(bind, checkfirst=True)
    _create_events()
    _create_champions()
    _create_duels()
    _create_tactic_votes()
    _create_sponsorships()


def downgrade() -> None:
    op.drop_index("ix_sponsorships_season_recipient", table_name="sponsorships")
    op.drop_table("sponsorships")
    op.drop_index("ix_br_tactic_votes_duel_faction", table_name="br_tactic_votes")
    op.drop_table("br_tactic_votes")
    op.drop_table("br_duels")
    op.drop_table("br_champions")
    op.drop_table("br_events")
    bind = op.get_bind()
    for enum_type in reversed(ENUMS):
        enum_type.drop(bind, checkfirst=True)
