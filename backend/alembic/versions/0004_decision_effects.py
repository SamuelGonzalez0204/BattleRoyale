"""decision effects, role affinity, decision closing and phase clock

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# El tipo ya existe desde 0001: solo se referencia.
user_role = postgresql.ENUM(
    "mercader", "guardia", "cronista", "explorador",
    name="user_role",
    create_type=False,
)

# Efectos y rol por plantilla, indexados por `order` (ver textos en 0003).
TEMPLATE_EFFECTS = {
    1: ("guardia", {"defensa": 8, "oro": -4}, {"oro": 6, "comida": 3, "defensa": -4}),
    2: ("mercader", {"oro": 5, "moral": -2}, {"comida": 6, "oro": 2, "moral": -3}),
    3: ("explorador", {"comida": 8, "moral": -5}, {"moral": 4, "comida": -6}),
    4: ("guardia", {"defensa": 7, "moral": -3, "comida": -2}, {"moral": 5, "defensa": -3}),
    5: ("cronista", {"moral": 8, "oro": -6, "comida": -2}, {"oro": 6, "moral": -4}),
    6: ("explorador", {"comida": 4, "oro": 4, "poblacion": -3}, {"defensa": 5, "moral": -2}),
    7: ("mercader", {"moral": 5, "oro": -5}, {"oro": 8, "moral": -4, "defensa": -2}),
    8: ("cronista", {"moral": 3, "poblacion": 2, "oro": -3}, {"defensa": 3, "moral": -3}),
}

EMPTY_JSON = sa.text("'{}'::jsonb")


def _add_effect_columns(table: str) -> None:
    op.add_column(table, sa.Column("effects_a", postgresql.JSONB, nullable=False, server_default=EMPTY_JSON))
    op.add_column(table, sa.Column("effects_b", postgresql.JSONB, nullable=False, server_default=EMPTY_JSON))
    op.add_column(table, sa.Column("role_affinity", user_role, nullable=True))


def _backfill_templates() -> None:
    templates = sa.table(
        "decision_templates",
        sa.column("order", sa.Integer),
        sa.column("effects_a", postgresql.JSONB),
        sa.column("effects_b", postgresql.JSONB),
        sa.column("role_affinity", user_role),
    )
    for order, (role, effects_a, effects_b) in TEMPLATE_EFFECTS.items():
        op.execute(
            templates.update()
            .where(templates.c.order == order)
            .values(effects_a=effects_a, effects_b=effects_b, role_affinity=role)
        )


def _backfill_decisions_from_templates() -> None:
    # Las decisiones ya creadas no guardan su plantilla: se emparejan por la pregunta.
    op.execute(
        sa.text(
            """
            UPDATE decisions AS d
            SET effects_a = t.effects_a,
                effects_b = t.effects_b,
                role_affinity = t.role_affinity
            FROM decision_templates AS t
            WHERE d.question = t.question
            """
        )
    )


def upgrade() -> None:
    _add_effect_columns("decision_templates")
    _add_effect_columns("decisions")
    op.add_column("decisions", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("decisions", sa.Column("winner", sa.String(1), nullable=True))
    op.create_check_constraint("ck_decision_winner", "decisions", "winner IS NULL OR winner IN ('a', 'b')")

    op.add_column("seasons", sa.Column("phase_started_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(sa.text("UPDATE seasons SET phase_started_at = started_at"))
    op.alter_column("seasons", "phase_started_at", nullable=False, server_default=sa.func.now())

    _backfill_templates()
    _backfill_decisions_from_templates()


def downgrade() -> None:
    op.drop_column("seasons", "phase_started_at")
    op.drop_constraint("ck_decision_winner", "decisions", type_="check")
    for column in ("winner", "closed_at", "role_affinity", "effects_b", "effects_a"):
        op.drop_column("decisions", column)
    for column in ("role_affinity", "effects_b", "effects_a"):
        op.drop_column("decision_templates", column)
